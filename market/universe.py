from pathlib import Path
import pandas as pd


class UniverseManager:
    """
    Handles loading the application's stock universe.
    """

    def __init__(self):
        self.master_file = (
            Path("data")
            / "universe"
            / "master_universe.csv"
        )

    def load_master_universe(self):
        """
        Loads the master universe CSV into a Pandas DataFrame.
        """

        if not self.master_file.exists():
            raise FileNotFoundError(
                f"Universe file not found:\n{self.master_file}"
            )

        return pd.read_csv(self.master_file)