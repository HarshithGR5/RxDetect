from app.services.validation.drug_normalizer import normalize_drug_name

tests = [
    "Thyronorm 50",
    "Ecosprin AV",
    "Pantop 40",
    "Combiflam",
    "Crocin 650",
]

for t in tests:
    print("\n---", t, "---")
    print(normalize_drug_name(t))