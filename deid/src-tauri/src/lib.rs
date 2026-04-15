use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter, LogicalPosition, LogicalSize, Manager, State, WindowEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_EVENT: &str = "backend:event";
const WINDOW_STATE_FILE: &str = "window-state.json";
const FALLBACK_MIN_WIDTH: f64 = 960.0;
const FALLBACK_MIN_HEIGHT: f64 = 680.0;

#[derive(Default)]
struct BackendRuntime {
    child: Option<Arc<Mutex<CommandChild>>>,
    ready: bool,
    feature_map: Vec<String>,
    startup_error: Option<String>,
}

type SharedBackendState = Arc<(Mutex<BackendRuntime>, Condvar)>;

#[derive(Serialize)]
struct BackendStatus {
    ready: bool,
    feature_map: Vec<String>,
    startup_error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct PersistedWindowState {
    width: f64,
    height: f64,
    x: f64,
    y: f64,
    maximized: bool,
}

fn window_state_path(app: &AppHandle) -> Option<PathBuf> {
    let path = app.path().app_data_dir().ok()?;
    Some(path.join(WINDOW_STATE_FILE))
}

fn load_window_state(app: &AppHandle) -> Option<PersistedWindowState> {
    let path = window_state_path(app)?;
    let raw = fs::read_to_string(path).ok()?;
    serde_json::from_str(&raw).ok()
}

fn save_window_state(app: &AppHandle, state: &PersistedWindowState) {
    let Some(path) = window_state_path(app) else {
        return;
    };
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if let Ok(encoded) = serde_json::to_string(state) {
        let _ = fs::write(path, encoded);
    }
}

fn compute_default_window_state(app: &AppHandle) -> PersistedWindowState {
    if let Some(window) = app.get_webview_window("main") {
        if let Ok(Some(monitor)) = window.current_monitor() {
            let monitor_size = monitor.size();
            let width = (monitor_size.width as f64 * 0.9).max(FALLBACK_MIN_WIDTH);
            let height = (monitor_size.height as f64 * 0.9).max(FALLBACK_MIN_HEIGHT);
            let x = monitor.position().x as f64 + ((monitor_size.width as f64 - width) / 2.0).max(0.0);
            let y =
                monitor.position().y as f64 + ((monitor_size.height as f64 - height) / 2.0).max(0.0);
            return PersistedWindowState {
                width,
                height,
                x,
                y,
                maximized: false,
            };
        }
    }
    PersistedWindowState {
        width: 1280.0,
        height: 860.0,
        x: 80.0,
        y: 80.0,
        maximized: false,
    }
}

fn clamp_window_state(app: &AppHandle, state: PersistedWindowState) -> PersistedWindowState {
    let mut clamped = state.clone();
    clamped.width = clamped.width.max(FALLBACK_MIN_WIDTH);
    clamped.height = clamped.height.max(FALLBACK_MIN_HEIGHT);

    let window = app.get_webview_window("main");
    if let Some(window) = window {
        if let Ok(Some(monitor)) = window.current_monitor() {
            let monitor_size = monitor.size();
            let monitor_pos = monitor.position();
            let max_width = (monitor_size.width as f64).max(FALLBACK_MIN_WIDTH);
            let max_height = (monitor_size.height as f64).max(FALLBACK_MIN_HEIGHT);
            clamped.width = clamped.width.min(max_width);
            clamped.height = clamped.height.min(max_height);

            let min_x = monitor_pos.x as f64;
            let min_y = monitor_pos.y as f64;
            let max_x = min_x + (monitor_size.width as f64 - clamped.width).max(0.0);
            let max_y = min_y + (monitor_size.height as f64 - clamped.height).max(0.0);
            clamped.x = clamped.x.clamp(min_x, max_x);
            clamped.y = clamped.y.clamp(min_y, max_y);
        }
    }
    clamped
}

fn apply_window_state(app: &AppHandle, state: &PersistedWindowState) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    if state.maximized {
        let _ = window.maximize();
        return;
    }
    let _ = window.set_size(LogicalSize::new(state.width, state.height));
    let _ = window.set_position(LogicalPosition::new(state.x, state.y));
}

fn persist_main_window_state(app: &AppHandle) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    let size = window.inner_size().ok();
    let pos = window.outer_position().ok();
    let maximized = window.is_maximized().ok().unwrap_or(false);
    if let (Some(size), Some(pos)) = (size, pos) {
        let state = PersistedWindowState {
            width: size.width as f64,
            height: size.height as f64,
            x: pos.x as f64,
            y: pos.y as f64,
            maximized,
        };
        save_window_state(app, &state);
    }
}

fn app_root_dir() -> Result<PathBuf, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .map(|path| path.to_path_buf())
        .ok_or_else(|| "Unable to resolve repository root".to_string())
}

fn notify_startup_error(state: &SharedBackendState, error: String) {
    let (lock, cvar) = &**state;
    let mut runtime = lock.lock().expect("backend state lock poisoned");
    runtime.startup_error = Some(error);
    cvar.notify_all();
}

fn handle_backend_stdout(app: &AppHandle, state: &SharedBackendState, line: &str) {
    let parsed = serde_json::from_str::<Value>(line);
    match parsed {
        Ok(message) => {
            let _ = app.emit(BACKEND_EVENT, message.clone());
            let message_type = message
                .get("type")
                .and_then(Value::as_str)
                .unwrap_or_default();
            if message_type == "READY" {
                let feature_map = message
                    .get("payload")
                    .and_then(|payload| payload.get("feature_map"))
                    .and_then(Value::as_array)
                    .map(|items| {
                        items
                            .iter()
                            .filter_map(Value::as_str)
                            .map(ToString::to_string)
                            .collect::<Vec<String>>()
                    })
                    .unwrap_or_default();

                let (lock, cvar) = &**state;
                let mut runtime = lock.lock().expect("backend state lock poisoned");
                runtime.ready = true;
                runtime.feature_map = feature_map;
                runtime.startup_error = None;
                cvar.notify_all();
                eprintln!("Received READY from backend sidecar.");
            }
        }
        Err(err) => {
            let synthetic_error = json!({
                "id": null,
                "type": "ERROR",
                "payload": {
                    "code": "RUST_PARSE_ERROR",
                    "message": format!("Failed to parse backend output line: {err}")
                }
            });
            let _ = app.emit(BACKEND_EVENT, synthetic_error);
        }
    }
}

fn spawn_backend(app: AppHandle, state: SharedBackendState) -> Result<(), String> {
    let root = app_root_dir()?;
    let command = if cfg!(debug_assertions) {
        let python = root
            .join("src-python")
            .join(".venv")
            .join("bin")
            .join("python");
        let script = root.join("src-python").join("__main__.py");
        app.shell()
            .command(python.to_string_lossy().to_string())
            .args([script.to_string_lossy().to_string()])
    } else {
        app.shell()
            .sidecar("deid-sidecar")
            .map_err(|err| format!("Failed to resolve sidecar command: {err}"))?
    };

    let (mut receiver, child) = command
        .spawn()
        .map_err(|err| format!("Failed to spawn backend process: {err}"))?;

    {
        let (lock, _) = &*state;
        let mut runtime = lock.lock().expect("backend state lock poisoned");
        runtime.child = Some(Arc::new(Mutex::new(child)));
    }

    let app_for_events = app.clone();
    let state_for_events = state.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = receiver.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let text = String::from_utf8_lossy(&bytes).to_string();
                    for line in text.lines() {
                        if line.trim().is_empty() {
                            continue;
                        }
                        handle_backend_stdout(&app_for_events, &state_for_events, line);
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    let text = String::from_utf8_lossy(&bytes).to_string();
                    eprintln!("[python-sidecar] {}", text.trim());
                }
                CommandEvent::Terminated(payload) => {
                    let message = format!(
                        "Backend terminated (code: {:?}, signal: {:?})",
                        payload.code, payload.signal
                    );
                    notify_startup_error(&state_for_events, message.clone());
                    let synthetic_error = json!({
                        "id": null,
                        "type": "ERROR",
                        "payload": {
                            "code": "BACKEND_TERMINATED",
                            "message": message
                        }
                    });
                    let _ = app_for_events.emit(BACKEND_EVENT, synthetic_error);
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(())
}

fn wait_for_ready(state: &SharedBackendState, timeout: Duration) -> Result<(), String> {
    let deadline = Instant::now() + timeout;
    let (lock, cvar) = &**state;
    let mut runtime = lock.lock().expect("backend state lock poisoned");
    loop {
        if runtime.ready {
            return Ok(());
        }
        if let Some(error) = &runtime.startup_error {
            return Err(error.clone());
        }
        let now = Instant::now();
        if now >= deadline {
            runtime.startup_error = Some("Timed out waiting for READY event".to_string());
            return Err("Timed out waiting for READY event".to_string());
        }
        let remaining = deadline.saturating_duration_since(now);
        let (next_runtime, _) = cvar
            .wait_timeout(runtime, remaining)
            .expect("backend state condvar wait failed");
        runtime = next_runtime;
    }
}

fn write_backend_line(state: &SharedBackendState, line: &str) -> Result<(), String> {
    let child_arc = {
        let (lock, _) = &**state;
        let runtime = lock.lock().expect("backend state lock poisoned");
        runtime
            .child
            .as_ref()
            .cloned()
            .ok_or_else(|| "Backend process is not running".to_string())?
    };
    let mut child = child_arc.lock().expect("backend child lock poisoned");
    child
        .write(line.as_bytes())
        .map_err(|err| format!("Failed to write backend message: {err}"))?;
    child
        .write(b"\n")
        .map_err(|err| format!("Failed to write backend newline: {err}"))?;
    Ok(())
}

#[tauri::command]
fn send_backend_command(state: State<SharedBackendState>, envelope: Value) -> Result<(), String> {
    if !envelope.is_object() {
        return Err("Envelope must be a JSON object".to_string());
    }
    let serialized = serde_json::to_string(&envelope)
        .map_err(|err| format!("Invalid command envelope: {err}"))?;
    write_backend_line(&state, &serialized)
}

#[tauri::command]
fn backend_status(state: State<SharedBackendState>) -> BackendStatus {
    let (lock, _) = &**state;
    let runtime = lock.lock().expect("backend state lock poisoned");
    BackendStatus {
        ready: runtime.ready,
        feature_map: runtime.feature_map.clone(),
        startup_error: runtime.startup_error.clone(),
    }
}

#[tauri::command]
fn shutdown_backend(state: State<SharedBackendState>) -> Result<(), String> {
    let envelope = json!({
        "id": "rust-shutdown",
        "command": "SHUTDOWN",
        "payload": {}
    });
    let serialized = serde_json::to_string(&envelope)
        .map_err(|err| format!("Failed to serialize SHUTDOWN: {err}"))?;
    write_backend_line(&state, &serialized)
}

#[tauri::command]
fn save_text_dialog(default_name: String, content: String) -> Result<String, String> {
    let Some(path) = rfd::FileDialog::new().set_file_name(&default_name).save_file() else {
        return Err("USER_CANCELLED".to_string());
    };
    fs::write(&path, content).map_err(|err| format!("Failed to write file: {err}"))?;
    Ok(path.to_string_lossy().to_string())
}

#[tauri::command]
fn save_binary_dialog(default_name: String, bytes: Vec<u8>) -> Result<String, String> {
    let Some(path) = rfd::FileDialog::new().set_file_name(&default_name).save_file() else {
        return Err("USER_CANCELLED".to_string());
    };
    fs::write(&path, bytes).map_err(|err| format!("Failed to write file: {err}"))?;
    Ok(path.to_string_lossy().to_string())
}

#[tauri::command]
fn read_clipboard_text() -> Result<String, String> {
    let mut clipboard = arboard::Clipboard::new()
        .map_err(|err| format!("Failed to access clipboard: {err}"))?;
    clipboard
        .get_text()
        .map_err(|err| format!("Failed to read clipboard: {err}"))
}

#[tauri::command]
fn write_clipboard_text(text: String) -> Result<(), String> {
    let mut clipboard = arboard::Clipboard::new()
        .map_err(|err| format!("Failed to access clipboard: {err}"))?;
    clipboard
        .set_text(text)
        .map_err(|err| format!("Failed to write clipboard: {err}"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_state: SharedBackendState =
        Arc::new((Mutex::new(BackendRuntime::default()), Condvar::new()));
    tauri::Builder::default()
        .manage(backend_state.clone())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let restored_state = load_window_state(&app_handle)
                .unwrap_or_else(|| compute_default_window_state(&app_handle));
            let clamped = clamp_window_state(&app_handle, restored_state);
            apply_window_state(&app_handle, &clamped);
            save_window_state(&app_handle, &clamped);

            if let Some(window) = app.get_webview_window("main") {
                let app_for_events = app_handle.clone();
                window.on_window_event(move |event| match event {
                    WindowEvent::Resized(_) | WindowEvent::Moved(_) => {
                        persist_main_window_state(&app_for_events);
                    }
                    _ => {}
                });
            }

            if let Err(err) = spawn_backend(app.handle().clone(), backend_state.clone()) {
                notify_startup_error(&backend_state, err.clone());
                eprintln!("{err}");
                return Ok(());
            }
            let backend_state_for_ready = backend_state.clone();
            std::thread::spawn(move || {
                if let Err(err) = wait_for_ready(&backend_state_for_ready, Duration::from_secs(10)) {
                    eprintln!("{err}");
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            send_backend_command,
            backend_status,
            shutdown_backend,
            save_text_dialog,
            save_binary_dialog,
            read_clipboard_text,
            write_clipboard_text
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
