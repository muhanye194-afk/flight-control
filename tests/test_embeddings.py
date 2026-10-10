from rag.embeddings import HASH_VECTOR_SIZE, hash_embedding


def main() -> None:
    first = hash_embedding("database connection pool exhausted")
    second = hash_embedding("database connection pool exhausted")
    different = hash_embedding("video edge routing failure")

    assert len(first) == HASH_VECTOR_SIZE
    assert first == second
    assert first != different
    assert abs(sum(value * value for value in first) - 1.0) < 1e-9

    print("Deterministic hash embedding test passed.")


if __name__ == "__main__":
    main()
