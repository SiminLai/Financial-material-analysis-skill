from typing import Dict, Any
from reflection.evaluators import BaseEvaluator


class MissingFieldsEvaluator(BaseEvaluator):
	name = "missing_fields"

	def __init__(self, required_fields=None):
		if required_fields is None:
			required_fields = ["revenue", "net_income", "eps"]
		self.required_fields = required_fields

	def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
		present = []
		missing = []
		for f in self.required_fields:
			if f in state and state.get(f) is not None:
				present.append(f)
			else:
				missing.append(f)

		score = 0.0
		if self.required_fields:
			score = len(present) / len(self.required_fields)

		internal_feedback = (
			"All required numeric fields present." if not missing else
			f"Missing fields: {', '.join(missing)}"
		)

		return {
			"name": self.name,
			"score": score,
			"internal_feedback": internal_feedback,
			"details": {"present": present, "missing": missing},
		}

