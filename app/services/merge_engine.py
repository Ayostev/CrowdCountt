# app/services/merge_engine.py

import time


class IdentityMergeEngine:
    """
    Identity Merge Engine

    Responsibilities
    ----------------
    • Merge matched identities
    • Maintain alias mappings
    • Resolve canonical IDs
    """

    def __init__(self):

        # merged_id -> master_id
        self.aliases = {}

        self.merge_history = []

    # =====================================
    # FIND ROOT ID
    # =====================================
    def resolve(self, global_id):

        while global_id in self.aliases:

            global_id = self.aliases[global_id]

        return global_id

    # =====================================
    # MERGE
    # =====================================
    def merge(
        self,
        source_id,
        target_id,
        confidence
    ):

        source_root = self.resolve(source_id)
        target_root = self.resolve(target_id)

        if source_root == target_root:
            return source_root

        master_id = min(
            source_root,
            target_root
        )

        merged_id = max(
            source_root,
            target_root
        )

        print(
            "[MERGE]",
            source_id,
            "->",
            target_id,
            confidence
        )

        self.aliases[merged_id] = master_id

        print(
            "[MERGE COUNT]",
            len(self.aliases)
        )

        self.merge_history.append({

            "master_id": master_id,

            "merged_id": merged_id,

            "confidence": round(
                confidence,
                2
            ),

            "timestamp": time.time()
        })

        return master_id

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        print(
            "[GET MERGE SUMMARY]",
            len(self.aliases)
        )

        return {

            "merged_identities": len(
                self.aliases
            ),

            "aliases": self.aliases,

            "history": self.merge_history
        }


merge_engine = IdentityMergeEngine()