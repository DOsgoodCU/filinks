import pandas as pd
import re
from difflib import SequenceMatcher

# === CONFIG ===
URL_COL = 'url'
SIMILARITY_THRESHOLD = 0.7
INPUT_FILE = "publications_data.csv"
OUTPUT_FILE = "publications_data_deduped.csv"

# === TEXT UTILITIES ===

def extract_href_and_text(url_html):
    """Extract href and visible text from an HTML <a> tag."""
    if pd.isna(url_html):
        return "", ""
    text = str(url_html)
    href_match = re.search(r'href="([^"]+)"', text)
    href = href_match.group(1) if href_match else ""
    visible = re.sub(r"<[^>]+>", "", text).strip()
    return href, visible


def extract_combined_url_text(url_html):
    """Normalize the URL by combining href and visible parts."""
    href, visible = extract_href_and_text(url_html)
    combined = f"{href} {visible}".lower()
    return re.sub(r"[^a-z0-9 ]", " ", combined)


def similarity(a, b):
    """Compute a string similarity ratio."""
    a = "" if pd.isna(a) else str(a)
    b = "" if pd.isna(b) else str(b)
    return SequenceMatcher(None, a, b).ratio()


def print_full_entry(df, idx):
    """Pretty-print a full entry with href/text split."""
    print(f"\nRow {idx}:")
    print("=" * 80)
    href, visible = extract_href_and_text(df.loc[idx, URL_COL])
    print(f"HREF: {href}")
    print(f"TEXT: {visible}")
    for col in df.columns:
        if col != URL_COL and not col.startswith("__"):
            print(f"{col.upper()}: {df.loc[idx, col]}")
    print("=" * 80)


def smart_cast(value):
    """Clean numeric-looking strings and remove unnecessary decimals."""
    if pd.isna(value):
        return ""
    s = str(value).strip()
    if re.fullmatch(r"\d+\.0+", s):
        return str(int(float(s)))
    elif re.fullmatch(r"\d+\.\d+", s):
        return str(float(s)).rstrip('0').rstrip('.')
    return s


def clean_dataframe(df):
    """Clean entire dataframe at the end — remove .0 and cast as strings."""
    df_clean = df.copy()
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].map(smart_cast)
    return df_clean


# === MAIN SCRIPT ===

def main():
    pd.set_option('display.max_colwidth', None)
    df = pd.read_csv(INPUT_FILE)
    df["__url_norm"] = df[URL_COL].apply(extract_combined_url_text).astype(str)

    i = 0
    while i < len(df):
        j = i + 1
        while j < len(df):
            url_sim = similarity(df.loc[i, "__url_norm"], df.loc[j, "__url_norm"])
            if url_sim >= SIMILARITY_THRESHOLD:
                print("\n" + "-" * 80)
                print(f"⚠️  Potential duplicate found (URL similarity={url_sim:.2f})")
                print("-" * 80)

                print_full_entry(df, i)
                print_full_entry(df, j)

                choice = input("\nMerge these? (y = merge, k = keep both, s = skip): ").lower().strip()
                if choice == "y":
                    merged_row = {}
                    for col in df.columns:
                        if col.startswith("__"):
                            continue
                        val1, val2 = str(df.loc[i, col]), str(df.loc[j, col])
                        if val1 == val2:
                            merged_row[col] = smart_cast(val1)
                        else:
                            print(f"\nColumn: {col}")
                            print(f"1: {val1}")
                            print(f"2: {val2}")
                            sel = input("Choose (1/2/custom): ").strip()
                            if sel == "1":
                                merged_row[col] = smart_cast(val1)
                            elif sel == "2":
                                merged_row[col] = smart_cast(val2)
                            else:
                                merged_row[col] = smart_cast(sel)
                    for k, v in merged_row.items():
                        df.at[i, k] = v
                    df = df.drop(index=j).reset_index(drop=True)
                    df.at[i, "__url_norm"] = extract_combined_url_text(df.loc[i, URL_COL])
                    print(f"✅ Merged and updated. ({len(df)} rows remaining)")
                    continue
                elif choice == "k":
                    print("Keeping both entries.")
                else:
                    print("Skipped.")
            j += 1
        i += 1

    df = df[[c for c in df.columns if not c.startswith("__")]]
    df = clean_dataframe(df)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Deduplicated file saved to {OUTPUT_FILE} (cleaned of .0 artifacts)")

if __name__ == "__main__":
    main()

