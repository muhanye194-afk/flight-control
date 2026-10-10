import subprocess
import sys


TEST_MODULES = [
    "tests.test_evidence_judge",
    "tests.test_policy_guard",
    "tests.test_run_store",
    "tests.test_specialist_agents",
    "tests.test_offline_decision_flow",
    "tests.test_api_smoke",
]


def main() -> None:
    for test_module in TEST_MODULES:
        print(f"\nRunning {test_module}...")

        subprocess.run(
            [sys.executable, "-m", test_module],
            check=True,
        )

    print("\nAll Flight Control regression tests passed.")


if __name__ == "__main__":
    main()