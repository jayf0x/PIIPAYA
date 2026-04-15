describe("DeID Ollama ask flow", () => {
  it("shows ask controls only when ollama config is enabled and performs ask flow", async function () {
    if (process.env.DEID_RUN_OLLAMA_E2E !== "1") {
      this.skip();
    }

    await browser.url("/");

    const advancedButton = await $("button=⚙️ Advanced Settings");
    await advancedButton.waitForEnabled({ timeout: 15000 });
    await advancedButton.click();

    const modal = await $("[aria-label='Advanced Settings']");
    await modal.waitForDisplayed({ timeout: 15000 });
    const toggleInput = await modal.$("//span[normalize-space()='Enable Ollama Assist']/following::input[@type='checkbox'][1]");
    const isChecked = await toggleInput.isSelected();
    if (!isChecked) {
      await toggleInput.click();
      await browser.pause(700);
    }

    const modelSelect = await modal.$("//span[normalize-space()='Model']/following::select[1]");
    const configuredModel = process.env.DEID_OLLAMA_MODEL || "qwen3.5:9b";
    await modelSelect.selectByAttribute("value", configuredModel).catch(async () => {
      await modelSelect.selectByAttribute("value", "gemma3:270m-it-qat");
    });
    await browser.pause(700);

    const closeButton = await modal.$("button=Close");
    await closeButton.click();
    await modal.waitForDisplayed({ timeout: 15000, reverse: true });

    const sourceInput = await $("textarea[placeholder='Drop or paste sensitive records...']");
    await sourceInput.setValue("David met Alice in Brussels.");

    const askTrigger = await $("section[aria-label='Input pane'] .magic-ai");
    await askTrigger.waitForDisplayed({ timeout: 15000 });
    await askTrigger.click();

    const askInput = await $("section[aria-label='Input pane'] .ai-popover input[type='text']");
    await askInput.waitForDisplayed({ timeout: 15000 });
    await askInput.setValue("Switch David with Bruce");

    const askButton = await $("section[aria-label='Input pane'] .ai-popover .ask-actions button=Ask");
    await askButton.click();

    const askResult = await $("section[aria-label='Input pane'] .ai-popover .ask-result");
    await askResult.waitForDisplayed({ timeout: 15000 });
    const text = await askResult.getText();
    await expect(text.length).toBeGreaterThan(0);
    if (configuredModel === "qwen3.5:9b") {
      await expect(text).toContain("Bruce");
      await expect(text).not.toContain("David");
    }
  });
});
