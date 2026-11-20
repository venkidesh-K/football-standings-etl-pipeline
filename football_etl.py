"""Football Standings ETL: API-Football -> pandas -> SQL Server (MERGE upsert)."""
import json
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ---------- Step 1: Extract ----------
API_KEY = "PASTE_YOUR_KEY_HERE"
BASE_URL = "https://v3.football.api-sports.io/standings"
headers = {"x-apisports-key": API_KEY}
params = {"league": 39, "season": 2023}

response = requests.get(BASE_URL, headers=headers, params=params)
print("Status:", response.status_code)

data = response.json()
print("Errors:", data["errors"])

with open("raw.json", "w") as f:
    json.dump(data, f, indent=2)
print("Saved raw.json")

# ---------- Step 2: Transform ----------
teams = data["response"][0]["league"]["standings"][0]
print(len(teams))

rows = []
for t in teams:
    rows.append({
        "rank": t["rank"],
        "team_id": t["team"]["id"],
        "team_name": t["team"]["name"],
        "points": t["points"],
        "goal_diff": t["goalsDiff"],
        "form": t["form"],
        "played": t["all"]["played"],
        "wins": t["all"]["win"],
        "draws": t["all"]["draw"],
        "losses": t["all"]["lose"],
        "goals_for": t["all"]["goals"]["for"],
        "goals_against": t["all"]["goals"]["against"],
        "league_id": 39,
        "season": 2023,
    })

df = pd.DataFrame(rows)
print(df)
print(df.shape)

# ---------- Step 3: Load into SQL Server ----------
SERVER = r"localhost\SQLEXPRESS"
DATABASE = "FootballDB"  # create it once in SSMS: CREATE DATABASE FootballDB;
DRIVER = "ODBC Driver 17 for SQL Server"
SQL_USER = ""      # leave blank for Windows Authentication
SQL_PASSWORD = ""
TARGET_TABLE = "league_standings"

query = {"driver": DRIVER, "TrustServerCertificate": "yes"}
if SQL_USER:
    url = URL.create("mssql+pyodbc", username=SQL_USER, password=SQL_PASSWORD,
                     host=SERVER, database=DATABASE, query=query)
else:
    query["trusted_connection"] = "yes"
    url = URL.create("mssql+pyodbc", host=SERVER, database=DATABASE, query=query)

engine = create_engine(url)

with engine.connect() as conn:
    print("Connected! Test result:", conn.execute(text("SELECT 1")).scalar())

create_sql = f"""
IF OBJECT_ID('dbo.{TARGET_TABLE}') IS NULL
CREATE TABLE dbo.{TARGET_TABLE} (
    league_id INT NOT NULL,
    season INT NOT NULL,
    team_id INT NOT NULL,
    team_name NVARCHAR(100),
    [rank] INT,
    played INT, wins INT, draws INT, losses INT,
    goals_for INT, goals_against INT, goal_diff INT,
    points INT,
    form NVARCHAR(20),
    PRIMARY KEY (league_id, season, team_id)
);
"""
with engine.begin() as conn:
    conn.execute(text(create_sql))
print("Table ready")

# Upsert: load into a staging table, then MERGE into the real table
staging = f"{TARGET_TABLE}_staging"
df.to_sql(staging, engine, schema="dbo", if_exists="replace", index=False)

merge_sql = f"""
MERGE dbo.{TARGET_TABLE} AS t
USING dbo.{staging} AS s
  ON t.league_id = s.league_id AND t.season = s.season AND t.team_id = s.team_id
WHEN MATCHED THEN UPDATE SET
  t.team_name = s.team_name, t.[rank] = s.[rank], t.played = s.played,
  t.wins = s.wins, t.draws = s.draws, t.losses = s.losses,
  t.goals_for = s.goals_for, t.goals_against = s.goals_against,
  t.goal_diff = s.goal_diff, t.points = s.points, t.form = s.form
WHEN NOT MATCHED THEN INSERT
  (league_id, season, team_id, team_name, [rank], played, wins, draws, losses,
   goals_for, goals_against, goal_diff, points, form)
VALUES
  (s.league_id, s.season, s.team_id, s.team_name, s.[rank], s.played, s.wins, s.draws,
   s.losses, s.goals_for, s.goals_against, s.goal_diff, s.points, s.form);
"""
with engine.begin() as conn:
    conn.execute(text(merge_sql))
    conn.execute(text(f"DROP TABLE dbo.{staging}"))

# Check the load
with engine.connect() as conn:
    n = conn.execute(text(f"SELECT COUNT(*) FROM dbo.{TARGET_TABLE}")).scalar()
print("Rows in table:", n)
