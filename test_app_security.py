import unittest
import pandas as pd
import io
from app import convert_df_to_csv

class TestAppSecurity(unittest.TestCase):
    def test_csv_injection_hardening(self):
        # Create a DataFrame with various dangerous formula triggers including variants
        # Ensure both columns have the same length
        data = {
            "name": ["Normal", "=Formula", "+Plus", "-Minus", "@At", "\tTab", "\rCR", "\nLF"],
            "fullwidth": ["Normal", "\uff1dEquals", "\uff0bPlus", "\uff0dMinus", "\uff20At", "Normal", "Normal", "Normal"]
        }
        df = pd.DataFrame(data)

        # Convert to CSV using the hardened function
        csv_bytes = convert_df_to_csv(df)
        csv_text = csv_bytes.decode("utf-8")

        # Parse the CSV back to check if single quotes were prepended
        output_df = pd.read_csv(io.StringIO(csv_text))

        # Check standard dangerous characters
        self.assertTrue(output_df["name"].iloc[1].startswith("'="))
        self.assertTrue(output_df["name"].iloc[2].startswith("'+"))
        self.assertTrue(output_df["name"].iloc[3].startswith("'-"))
        self.assertTrue(output_df["name"].iloc[4].startswith("'@"))
        self.assertTrue(output_df["name"].iloc[5].startswith("'\t"))
        self.assertTrue(output_df["name"].iloc[6].startswith("'\r"))
        self.assertTrue(output_df["name"].iloc[7].startswith("'\n"))

        # Check fullwidth Unicode variants
        self.assertTrue(output_df["fullwidth"].iloc[1].startswith("'\uff1d"))
        self.assertTrue(output_df["fullwidth"].iloc[2].startswith("'\uff0b"))
        self.assertTrue(output_df["fullwidth"].iloc[3].startswith("'\uff0d"))
        self.assertTrue(output_df["fullwidth"].iloc[4].startswith("'\uff20"))

        # Verify that normal text is NOT modified
        self.assertEqual(output_df["name"].iloc[0], "Normal")
        self.assertEqual(output_df["fullwidth"].iloc[0], "Normal")

if __name__ == "__main__":
    unittest.main()
