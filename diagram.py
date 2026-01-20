import plotly.graph_objects as go

# pip install -U kaleido

# Define nodes
nodes = [
    ("dim_channels", "PK: channel_key\n• channel_name\n• channel_type\n• first_post_date\n• avg_views"),
    ("dim_dates", "PK: date_key\n• full_date\n• day_of_week\n• is_weekend\n• quarter/year"),
    ("fct_messages", "PK: message_id\n• message_text\n• view_count\n• forward_count\n• has_image"),
    ("stg_telegram_messages", "Data cleaning\nType casting\nBusiness logic")
]

# Node positions
positions = {
    "dim_channels": (0, 2),
    "dim_dates": (2, 2),
    "fct_messages": (1, 1),
    "stg_telegram_messages": (1, 0)
}

# Create figure
fig = go.Figure()

# Add nodes
for node, label in nodes:
    x, y = positions[node]
    fig.add_trace(go.Scatter(
        x=[x], y=[y],
        text=[f"<b>{node}</b><br>{label}"],
        mode="text",
        hoverinfo='text'
    ))

# Add edges
edges = [
    ("stg_telegram_messages", "fct_messages"),
    ("fct_messages", "dim_channels"),
    ("fct_messages", "dim_dates")
]

for start, end in edges:
    x0, y0 = positions[start]
    x1, y1 = positions[end]
    fig.add_trace(go.Scatter(
        x=[x0, x1], y=[y0, y1],
        mode="lines",
        line=dict(width=2, color="gray"),
        hoverinfo='none'
    ))

# Layout
fig.update_layout(
    title="Star Schema: Telegram Medical Data Warehouse",
    showlegend=False,
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    plot_bgcolor="white",
    margin=dict(l=20, r=20, t=50, b=20)
)

# Save as PNG
fig.write_image("telegram_star_schema.png")  # Output file
fig.show()
