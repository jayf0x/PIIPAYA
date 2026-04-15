from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry


class NarronymousEngine:
    def __init__(self, model="en_core_web_lg"):
        self.name_map = {}

        # NLP setup
        nlp_configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": model}],
        }

        nlp_engine = NlpEngineProvider(
            nlp_configuration=nlp_configuration
        ).create_engine()

        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(nlp_engine=nlp_engine)

        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            registry=registry
        )

        self.anonymizer = AnonymizerEngine()

    def get_pseudonym(self, original_text):
        if original_text not in self.name_map:
            self.name_map[original_text] = f"FakeUser_{len(self.name_map)}"
        return self.name_map[original_text]

    def run(self, text):
        results = self.analyzer.analyze(
            text=text,
            entities=None,
            language="en",
            score_threshold=0.35,
        )

        operators = {
            "PERSON": OperatorConfig(
                "custom",
                {"lambda": lambda x: self.get_pseudonym(x)}
            )
        }

        return self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )


engine = NarronymousEngine()

raw_text = """
Kate's social security number is 078-05-1126.
Her driver license? it is 1234567A.
"""

result = engine.run(raw_text)

print(result)