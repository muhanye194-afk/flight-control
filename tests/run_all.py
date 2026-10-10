import os
import subprocess
import sys


TEST_MODULES = [
    "tests.test_evidence_judge",
    "tests.test_policy_guard",
    "tests.test_run_store",
    "tests.test_specialist_agents",
    "tests.test_offline_decision_flow",
    "tests.test_api_smoke",
    "tests.test_embeddings",
]


def main() -> None:
    test_environment = os.environ.copy()
    test_environment.setdefault(
        "FLIGHT_CONTROL_EMBEDDING_BACKEND",
        "hash",
    )

    for test_module in TEST_MODULES:
        print(f"\nRunning {test_module}...")

        subprocess.run(
            [sys.executable, "-m", test_module],
            check=True,
            env=test_environment,
        )

    print("\nAll Flight Control regression tests passed.")


if __name__ == "__main__":
    main()
