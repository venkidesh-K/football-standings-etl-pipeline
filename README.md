# Football Standings ETL Pipeline

An end-to-end ETL pipeline: it collects live Premier League table data from the API-Football REST API, cleans it with pandas, stores it in SQL Server, and feeds a two-page Power BI dashboard (`ETL_EPL_2024.pbix`). A staging table and MERGE upsert mean you can rerun it daily with no duplicate rows.

**Pipeline:** API-Football (REST) -> Python (requests, pandas) -> SQL Server (SQLAlchemy) -> Power BI

## Tools
Python, requests, pandas, SQLAlchemy, pyodbc, SQL Server and SSMS. Power BI for the dashboard.

## How it works
1. **Extract:** a GET request to `v3.football.api-sports.io/standings` (league 39, season 2023). The raw reply is saved as `raw.json`, so data can be reprocessed without calling the API again.
2. **Transform:** a loop reads each team's nested JSON and builds a clean pandas DataFrame of 20 teams and 14 columns (rank, points, wins, draws, losses, goals for/against, goal difference, form).
3. **Load:** SQLAlchemy creates `dbo.league_standings` (primary key: league, season, team) if needed, loads the data into a staging table, runs a T-SQL `MERGE` to update existing rows and insert new ones, then drops the staging table.
4. **Verify:** a row count check after the load (expect 20).
5. **Visualize:** the Power BI dashboard `ETL_EPL_2024.pbix` reads the SQL Server table (`standings_2024`, 2024 season) and has 2 pages.

## Dashboard
The dashboard (`ETL_EPL_2024.pbix`, 2 pages) covers position, points, wins, draws and losses, home and away wins, goals scored and conceded, goal difference, goals per match and form.

## How to run
1. `pip install -r requirements.txt`
2. In SSMS, run `CREATE DATABASE FootballDB;` once. Check your driver name with `import pyodbc; print(pyodbc.drivers())`.
3. In `football_etl.py`, replace `PASTE_YOUR_KEY_HERE` with your API-Football key, and set `SERVER` and `DRIVER` for your machine. Leave `SQL_USER` blank to use Windows Authentication. Never commit a real key.
4. `python football_etl.py`. You should see status 200, empty errors, "Connected! Test result: 1", and "Rows in table: 20".
5. Open `ETL_EPL_2024.pbix` in Power BI Desktop, or build your own: Get data > SQL Server > server + `FootballDB` > Import > tick `league_standings` > Load. To refresh later, rerun the script and click Refresh.

## Troubleshooting
| Error | Fix |
|---|---|
| `KeyError: 'team.id'` | Read nested values with a loop, as in the script |
| Named Pipes / could not open a connection | Copy the exact server name from SSMS and start the SQL Server service |
| Cannot open database FootballDB | Run `CREATE DATABASE FootballDB;` |
| Data source name not found | Copy the driver name exactly from `pyodbc.drivers()` |
| Login failed | Leave `SQL_USER` blank for Windows Authentication |
| Empty response or IndexError | Check `data["errors"]`; try season 2022 |

## Future improvements
Load several leagues and seasons, schedule a daily run, add top scorers and fixtures, and keep the API key in an environment variable.

Note: the script is set to season 2023 as a default; change `season` in `params` and `df` (for example to 2024) to match the dashboard.

A step-by-step explanation of the whole project is in `Football_ETL_Project_Guide.docx`.


## Screenshots
> **[Placeholder: add a screenshot of each dashboard page here]**
