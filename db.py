# supabase Datenzugrifffrom supabase import create_client
from dotenv import load_dotenv
import os
from supabase import create_client


load_dotenv()  # liest .env

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# --- Peaks ---------------------------------
def upsert_peaks(records: list[dict]):
    return supabase.table("peaks").upsert(records).execute()

def get_all_peaks():
    return supabase.table("peaks").select("*").execute().data

# --- Ascents -------------------------------
def insert_ascents(records: list[dict]):
    return supabase.table("ascents").insert(records).execute()

def get_user_ascents(user_id: str | None = None):
    q = supabase.table("ascents").select("*")
    if user_id:
        q = q.eq("user_id", user_id)
    return q.execute().data
