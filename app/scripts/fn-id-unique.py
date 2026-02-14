import sys
import pathlib
from functools import partial
from typing import Any

# Ensure project root is on sys.path so this file can be run directly
# when invoked as `python app/services/testing.py`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from app.services.filesystem_service import suggest_file_node_id


# 1) Standalone verifier function
def my_verify(node_id: str) -> bool:
	"""Return True when the id is available (not present in DB)."""
	# Replace this stub with your real DB lookup
	def lookup_in_db(nid: str) -> bool:
		if nid == "buscard-carpenter-homedepot_010_20260101":
			return True # yes, it is here.
		return False # not found

	return not lookup_in_db(node_id)


# 2) Bound method on an object (useful with a Neo4j session)
class Neo4jVerifier:
	def __init__(self, session: Any):
		self.session = session

	def verify_node_uniqueness(self, node_id: str) -> bool:
		"""Return True if no FileNode exists with given FILE-NODE-id."""
		# Example Cypher — adapt to your driver/session API
		result = self.session.run(
			"MATCH (n:FileNode {`FILE-NODE-id`:$id}) RETURN count(n) AS c",
			id=node_id
		)
		record = result.single()
		count = record.get("c", 0) if record else 0
		return count == 0


# 3) Using functools.partial to bind extra args to a verifier
def verify_with_conn(node_id: str, conn) -> bool:
	# conn would be a DB helper with an `exists` method
	return not conn.exists(node_id)


if __name__ == "__main__":
	# test_path = "./some/nonexistent-2026_0123-example_001.pdf"
	test_path = "./1402_1010-ancient-document.txt"

	# Example: call with the simple standalone function
	uid = suggest_file_node_id(test_path, verify_node_uniqueness=my_verify, raise_on_missing=False)
	print("standalone verifier ->", uid)

	# Example: call with the placeholder example_verify via partial
	verifier = partial(
		verify_with_conn,
		conn=type('C', (), {'exists': staticmethod(lambda x: False)})()
	)
	uid2 = suggest_file_node_id(test_path, verify_node_uniqueness=verifier, raise_on_missing=False)
	print("partial-based verifier ->", uid2)