# streamlit_app.py
import os, time, json
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from google import genai

# ── 1) Init GenAI Client ──────────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    st.error("Missing GEMINI_API_KEY — AI disabled.")
    st.stop()
client = genai.Client(api_key=GEMINI_API_KEY)

# ── 2) UI Setup ─────────────────────────────────────────────
st.set_page_config(page_title="Shopify Import Builder", layout="centered")
st.title("🍭️ Shopify CSV Builder with Gemini-Enhanced Tags & Descriptions")

# Sidebar: choose one mode
mode = st.sidebar.radio(
    "Select processing mode:",
    options=[
        "Default template (no AI)",
        "Simple mode (first sentence + tags)",
        "Full AI mode (custom description + tags)"
    ],
    index=0,
    help="Default: uses a static template; Simple: first sentence + AI tags; Full: AI description + tags."
)

uploaded_file = st.file_uploader("1) Upload CSV/Excel", type=["csv", "xlsx"])
if not uploaded_file:
    st.info("Awaiting file upload…")
    st.stop()

# ── 3) Load & Preview Raw Data ───────────────────────────────────────
try:
    df_raw = pd.read_excel(uploaded_file) if uploaded_file.name.lower().endswith(".xlsx") else pd.read_csv(uploaded_file)
    st.success(f"Loaded `{uploaded_file.name}` with {len(df_raw)} rows")
    st.subheader("📋 Raw Data Preview")
    st.dataframe(df_raw.head(10))
except Exception as e:
    st.error(f"Could not load file: {e}")
    st.stop()

# ── 4) Define AI helper funcs ───────────────────────────────────────
def refine_and_tag(text: str) -> tuple[str, str]:
    prompt = (
        "You are a top-tier Shopify copywriter.\n"
        "1) Rewrite this product description to be clear, engaging, and on-brand.\n"
        "2) Then output on the next line exactly five comma-separated tags.\n\n"
        f"Original description:\n\"\"\"\n{text}\n\"\"\"\n\n"
        "Respond with exactly two lines:\n"
        "- Line 1: your rewritten description\n"
        "- Line 2: tag1,tag2,tag3,tag4,tag5"
    )
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    parts = (resp.text or "").strip().split("\n", 1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")

def tags_only(text: str) -> str:
    prompt = (
        "You are an expert Shopify copywriter.\n"
        "Suggest exactly five comma-separated Shopify tags for this product description:\n\n"
        f"\"\"\"\n{text}\n\"\"\"\n\n"
        "Respond with a single line:\n"
        "tag1,tag2,tag3,tag4,tag5"
    )
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return (resp.text or "").strip()

# ── 5) Process trigger ───────────────────────────────────────
if st.button("2) Process Data"):
    df = df_raw.copy()
    n = len(df)
    progress = st.progress(0)
    custom_descs, all_tags = [], []

    with st.spinner("🔮 Processing data…"):
        for i, (_, row) in enumerate(df.iterrows()):
            original = row.get("description", "") or ""
            if mode == "Default template (no AI)":
                desc = f"{row.get('title', '').strip()} - {row.get('product category', '').strip()}"
                tags = ""
            elif mode == "Simple mode (first sentence + tags)":
                first_sent = original.split(".", 1)[0].strip()
                desc = first_sent
                tags = tags_only(first_sent)
            else:
                desc, tags = refine_and_tag(original)

            custom_descs.append(desc)
            all_tags.append(tags)
            progress.progress((i + 1) / n)
            time.sleep(0.2)

    df["custom_description"] = custom_descs
    df["ai_tags"] = all_tags

    df["sizes_list"] = df["size"].fillna("").str.split(r"\s*,\s*")
    df["colours_list"] = df["colour"].fillna("").str.split(r"\s*,\s*")
    df = df.explode("sizes_list").explode("colours_list")

    # Interactive quantity input
    st.subheader("🧮 Enter Quantity Per Variant")
    unique_variants = df[["sizes_list", "colours_list"]].drop_duplicates().values.tolist()
    variant_qty_map = {}
    for size, color in unique_variants:
        key = f"qty_{size}_{color}"
        qty = st.number_input(f"Quantity for Size: {size}, Color: {color}", min_value=0, value=10, step=1, key=key)
        variant_qty_map[(str(size).strip(), str(color).strip())] = qty

    df["Variant Inventory Qty"] = df.apply(lambda row: variant_qty_map.get((str(row["sizes_list"]).strip(), str(row["colours_list"]).strip()), 0), axis=1)

    df["_base_handle"] = df["title"].str.strip().str.replace(r"\s+","-", regex=True).str.lower()
    serials = {h: str(idx+1).zfill(2) for idx,h in enumerate(df["_base_handle"].unique())}
    df["_serial"] = df["_base_handle"].map(serials)
    df["Handle"] = df["_base_handle"] + "-" + df["_serial"]

    out = pd.DataFrame({
        "Handle": df["Handle"],
        "Title": df["title"],
        "Body (HTML)": "<p>" + df["custom_description"] + "</p>",
        "Vendor": "YourBrandName",
        "Product Category": df["product category"].fillna(""),
        "Type": df["type"].fillna(""),
        "Tags": df["ai_tags"],
        "Published": df["published"].astype(str).str.lower().eq("active").map({True:"TRUE",False:"FALSE"}),
        "Option1 Name": "Size",
        "Option1 Value": df["sizes_list"],
        "Option2 Name": "Color",
        "Option2 Value": df["colours_list"],
        "Variant SKU": df["product code"].fillna("") + "-" + df["_serial"] + "-" + df["sizes_list"] + "-" + df["colours_list"],
        "Variant Grams": 0,
        "Variant Inventory Tracker": df.get("Variant Inventory Tracker", pd.Series("")).fillna(""),
        "Variant Inventory Qty": df["Variant Inventory Qty"],
        "Variant Inventory Policy": df.get("Variant Inventory Policy", pd.Series("")).fillna(""),
        "Variant Fulfillment Service":"manual",
        "Variant Price": df.get("Variant Price", pd.Series(0)).fillna(0),
        "Variant Compare At Price": df.get("Variant Compare At Price", pd.Series(0)).fillna(0),
        "Variant Requires Shipping":"TRUE",
        "Variant Taxable": "TRUE",
        "Status": df.get("Status", pd.Series("")).fillna("")
    })

    st.subheader("📦 Processed Preview (first 10 rows)")
    st.dataframe(out.head(10))

    st.download_button(
        label="3) 📅 Download Shopify CSV",
        data=out.to_csv(index=False).encode("utf-8"),
        file_name="shopify_ready.csv",
        mime="text/csv"
    )

    st.markdown("""
    ### ℹ️ Quantity Input Format Instructions:
    You can now directly enter quantities for each size-color variant after upload.
    """)
#this app is done now