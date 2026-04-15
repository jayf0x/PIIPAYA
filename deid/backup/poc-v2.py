import os
import yaml
import sqlite3
import hashlib
import math
import unicodedata
import concurrent.futures
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# ---------------------------------------------------------
# 1. Configuration (Initial Human-Readable)
# ---------------------------------------------------------
DEFAULT_CONFIG = """
db_path: "narronymous.db"
generator:
  seed: "global_salt_v1"
  likeliness: 1.0
  consistency: 0.1
normalization:
  lowercase: true
  strip_accents: true
  split_by_space: true
initial_name_pool:
  - Alice
  - Bob
  - Charlie
  - Derrick
  - Edith
  - Frank
  - Gertrude
  - Hank
  - Ivy
  - Johan
  - Lancaster
  - Swart
  - Thompson
"""

# ---------------------------------------------------------
# 2. Database Manager (Source of Truth)
# ---------------------------------------------------------
class DatabaseManager:
    """Handles the persistent Library of names. No session PII stored here."""
    def __init__(self, db_path, initial_names=None):
        self.db_path = db_path
        self._init_db(initial_names)

    def _init_db(self, initial_names):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS name_pool (name TEXT UNIQUE)")
            # Only populate if empty
            cursor = conn.execute("SELECT COUNT(*) FROM name_pool")
            if cursor.fetchone()[0] == 0 and initial_names:
                conn.executemany("INSERT INTO name_pool (name) VALUES (?)", 
                                 [(n,) for n in initial_names])

    def get_pool(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM name_pool ORDER BY name ASC")
            return [row[0] for row in cursor.fetchall()]

# ---------------------------------------------------------
# 3. Deterministic Mapping Logic
# ---------------------------------------------------------
class NarronymousMapper:
    def __init__(self, pool, config):
        self.pool = pool
        self.N = len(pool)
        self.cfg = config['generator']
        self.norm = config['normalization']

    def _normalize(self, text):
        if self.norm['strip_accents']:
            text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
        if self.norm['lowercase']:
            text = text.lower()
        return "".join(text.split())

    def _hash(self, text):
        return int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)

    def _get_deterministic_index(self, value):
        """Maps alphabetical proximity to index proximity."""
        weight = 0.0
        for i, char in enumerate((value.ljust(3, 'a'))[:3]):
            char_val = max(0, min(25, ord(char) - 97))
            weight += char_val / (26 ** (i + 1))
        
        base_idx = int(weight * self.N)
        # Offset influenced by seed/likeliness
        chaos = (self._hash(self.cfg['seed'] + value) % self.N) * (1 - self.cfg['likeliness'])
        return int((base_idx * self.cfg['likeliness']) + chaos) % self.N

    def map_token(self, token):
        val = self._normalize(token)
        idx = self._get_deterministic_index(val)
        
        # 'Step' is derived from hash of the value to keep it 100% deterministic 
        # regardless of processing order in multi-threading.
        step = self._hash(val) % 100
        drift = (math.sin(step * self.cfg['consistency'])) * 2
        
        base_name = self.pool[idx]
        # Boring mutation: append 'son' if drift is high
        return base_name + ("son" if drift > 1.5 else "")

# ---------------------------------------------------------
# 4. Engine (Process Orchestrator)
# ---------------------------------------------------------
class NarronymousEngine:
    def __init__(self, db_manager, config):
        self.config = config
        self.mapper = NarronymousMapper(db_manager.get_pool(), config)
        self.session_map = {} # EPHEMERAL: Cleared when object is destroyed

        # NLP Setup
        nlp_config = {"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]}
        engine_provider = NlpEngineProvider(nlp_configuration=nlp_config)
        self.analyzer = AnalyzerEngine(nlp_engine=engine_provider.create_engine())
        self.anonymizer = AnonymizerEngine()

    def _get_pseudonym(self, original_text):
        """Standardizes multi-word names and manages the session-only cache."""
        if original_text not in self.session_cache:
            if self.config['normalization']['split_by_space']:
                parts = original_text.split()
                pseudo = " ".join([self.mapper.map_token(p) for p in parts])
            else:
                pseudo = self.mapper.map_token(original_text)
            self.session_cache[original_text] = pseudo
        return self.session_cache[original_text]

    def process_text(self, text):
        self.session_cache = {} # Fresh start for every 'run' to ensure privacy
        
        results = self.analyzer.analyze(text=text, entities=["PERSON"], language="en")
        operators = {"PERSON": OperatorConfig("custom", {"lambda": lambda x: self._get_pseudonym(x)})}
        
        return self.anonymizer.anonymize(text=text, analyzer_results=results, operators=operators).text

# ---------------------------------------------------------
# 5. Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    # Load YAML once
    if not os.path.exists("config.yaml"):
        with open("config.yaml", "w") as f: f.write(DEFAULT_CONFIG)
    with open("config.yaml", "r") as f: yaml_cfg = yaml.safe_load(f)

    # DB takes over as Source of Truth for the name library
    db = DatabaseManager(yaml_cfg['db_path'], yaml_cfg['initial_name_pool'])
    
    engine = NarronymousEngine(db, yaml_cfg)

    raw_input = """
    Johan Thompson met with Derrick Lancaster. 
    Later, Johan and Derrick spoke with Hank Thompson.
    """

    print("--- Original ---")
    print(raw_input.strip())
    
    print("\n--- Anonymized (Session Persistent) ---")
    print(engine.process_text(raw_input).strip())

    # Verify no PII leaked into DB
    print("\n--- DB Check (Only the Pool) ---")
    print(f"Pool size in DB: {len(db.get_pool())} names.")