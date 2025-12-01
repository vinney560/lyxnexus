from rich.console import Console
from rich.table import Table

console = Console()

# Sample sales data
sales_data = [
    {"region": "North", "q1": 150000, "q2": 165000, "q3": 142000, "q4": 178000},
    {"region": "South", "q1": 120000, "q2": 135000, "q3": 148000, "q4": 162000},
    {"region": "East", "q1": 95000, "q2": 110000, "q3": 125000, "q4": 118000},
    {"region": "West", "q1": 180000, "q2": 195000, "q3": 172000, "q4": 205000},
]

table = Table(title="🏢 Quarterly Sales Report")
table.add_column("Region", style="bold cyan")
table.add_column("Q1", justify="right")
table.add_column("Q2", justify="right")
table.add_column("Q3", justify="right")
table.add_column("Q4", justify="right")
table.add_column("Total", justify="right", style="bold yellow")
table.add_column("Growth", justify="center")

for region_data in sales_data:
    region = region_data["region"]
    q1 = region_data["q1"]
    q2 = region_data["q2"]
    q3 = region_data["q3"]
    q4 = region_data["q4"]
    total = q1 + q2 + q3 + q4
    growth = ((q4 - q1) / q1) * 100
    
    # Color code growth
    if growth > 20:
        growth_display = f"[bright_green]+{growth:.1f}%[/bright_green]"
    elif growth > 0:
        growth_display = f"[green]+{growth:.1f}%[/green]"
    elif growth < -10:
        growth_display = f"[red]{growth:.1f}%[/red]"
    else:
        growth_display = f"[yellow]{growth:.1f}%[/yellow]"
    
    table.add_row(
        region,
        f"${q1:,}",
        f"${q2:,}",
        f"${q3:,}",
        f"${q4:,}",
        f"${total:,}",
        growth_display
    )

console.print(table)