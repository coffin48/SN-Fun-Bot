import logging
import sys

# ---- Logger setup ----
logger = logging.getLogger("sn_fun_bot")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ---- CSV Loader ----
def log_csv_loaded(df):
    if df.empty:
        logger.info("CSV K-pop gagal dimuat atau kosong.")
    else:
        total_rows = len(df)
        total_groups = df['Group'].nunique() if 'Group' in df.columns else 0
        total_members = df[['Stage Name','Korean Stage Name','Full Name']].apply(lambda x: x.notna().sum(), axis=1).sum()
        logger.info(f"CSV K-pop berhasil dimuat: {total_rows} baris | {total_groups} grup unik | {total_members} member terdeteksi")

# ---- Redis Cache ----
def log_cache_set(category, name):
    logger.info(f"Ringkasan {category}:{name} tersimpan di Redis.")

def log_cache_hit(category, name):
    logger.info(f"Mengambil ringkasan {category}:{name} dari Redis.")

# ---- Command !sn ----
def log_sn_command(user, input_text, category, detected_name=None):
    if category in ["GROUP", "MEMBER", "MEMBER_GROUP"]:
        logger.info(f"{user} memanggil !sn '{input_text}' → kategori: {category}, target: {detected_name}")
    elif category == "MULTIPLE":
        logger.info(f"{user} memanggil !sn '{input_text}' → kategori: {category}, multiple matches detected")
    elif category in ["OBROLAN", "REKOMENDASI"]:
        logger.info(f"{user} memanggil !sn '{input_text}' → kategori: {category}")
    else:
        logger.info(f"{user} memanggil !sn '{input_text}' → kategori: {category}")
