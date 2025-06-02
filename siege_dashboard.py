import pandas as pd
import os
import typing_extensions
import dash
from dash import dcc, html, Input, Output, dash_table, State, ctx
import plotly.express as px
import dash_bootstrap_components as dbc

# Read the current siege data
df = pd.read_csv("Siege_Data.csv")
df["Timestamp"] = pd.to_datetime(df["Timestamp"], format = "%y%m%d_%H%M")
df['DPS'] = pd.to_numeric(df['DPS'], errors='coerce')


# Get unique bosses and classes
# Bosses and classes
bosses = sorted(df['Boss'].unique())
classes = sorted(df['Class'].dropna().unique())

# App setup
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Siege DPS Dashboard"

# Layout
app.layout = html.Div([
    html.H2("Siege DPS Dashboard"),
    html.P("by Cruellia", style={'fontSize': '0.9rem', 'color': 'gray', 'marginTop': '-0.5rem', 'marginBottom': '0.5rem'}),
    html.Div(id='last-update', style={'fontSize': '0.8rem', 'color': 'gray', 'marginBottom': '1rem'}),

    # Podium section
    html.Div(id='podium', style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '2rem'}),

    html.Div([
        html.Label("Select Boss:"),
        dcc.Dropdown(
            id='boss-filter',
            options=[{'label': b, 'value': b} for b in bosses],
            value='Petrification Incarnate',
            clearable=False
        )
    ], style={'width': '30%', 'marginBottom': '1rem'}),

    dbc.Row([
        dbc.Col([
            html.Div(id='class-tables', style={'display': 'flex', 'flexDirection': 'column'})
        ], width=12)
    ]),

    html.Div([
        html.Label("Compare Players (type to filter):"),
        dcc.Dropdown(id='player-filter', options=[], multi=True, placeholder="Enter player names...", value=["Cruellia", "Mika"]),
        dcc.Graph(id='comparison-plot')
    ], style={'marginTop': '3rem'})
])

# Utility to build per-class tables
def build_table(class_name, dff_class):
    dff_class = dff_class.copy()
    dff_class['DPS'] = dff_class['DPS'].round(0).astype(int).apply(lambda x: f"{x:,}".replace(",", "."))

    columns = [
        {'name': 'Rank', 'id': 'Rank'},
        {'name': 'Player', 'id': 'Player', 'presentation': 'markdown'},
    ]
    if 'Class' in dff_class.columns:
        columns.append({'name': 'Class', 'id': 'Class'})
    columns.append({'name': 'DPS', 'id': 'DPS'})

    return html.Div([
        html.H5(class_name),

        dash_table.DataTable(
            id={'type': 'dps-table', 'index': class_name},
            columns=columns,
            data=dff_class.to_dict('records'),
            style_cell={'textAlign': 'left'},
            style_table={'overflowX': 'auto'},
            page_size=10,
            cell_selectable=False
        )
    ], style={'marginBottom': '2rem'})

# Update podium and class tables
@app.callback(
    Output('class-tables', 'children'),
    Output('podium', 'children'),
    Output('last-update', 'children'),
    Output('player-filter', 'options'),
    Input('boss-filter', 'value')
)
def update_tables_and_podium(selected_boss):
    tables = []
    all_players = []

    # Combined all-classes table
    combined_df = df[df['Boss'] == selected_boss]
    max_dps_df = combined_df.sort_values('DPS', ascending=False).groupby('Player', as_index=False).first()

    max_dps_with_tag = []
    for _, row in max_dps_df.iterrows():
        player_rows = combined_df[combined_df['Player'] == row['Player']].sort_values('Timestamp')
        is_new = row['DPS'] == player_rows.iloc[-1]['DPS']
        if is_new:
            player_name = f"{row['Player']} **🔥 (new!)**"
        else:
            player_name = row['Player']
        max_dps_with_tag.append({'Player': player_name, 'DPS': row['DPS'], 'Class': row['Class']})

    final_df = pd.DataFrame(max_dps_with_tag)
    final_df['Rank'] = final_df['DPS'].rank(ascending=False, method='first').astype(int)
    final_df = final_df.sort_values('DPS', ascending=False)[['Rank', 'Player', 'Class', 'DPS']]
    combined_table = build_table("All Classes", final_df)
    tables.append(combined_table)
    all_players.extend(final_df['Player'].str.replace(" **🔥 (new!)**", "", regex=False).tolist())

    # Podium from all players (not class-restricted)
    podium_df = df[df['Boss'] == selected_boss]
    top3_df = podium_df.sort_values('DPS', ascending=False).drop_duplicates('Player').head(3)
    podium_icons = ["🥇", "🥈", "🥉"]
    podium = []
    for i, (_, row) in enumerate(top3_df.iterrows()):
        icon = podium_icons[i] if i < len(podium_icons) else ""
        podium.append(
            html.Div([
                html.Div(icon, style={'fontSize': '2rem'}),
                html.Div(row['Player'], style={'fontWeight': 'bold'})
            ], style={'margin': '0 2rem', 'textAlign': 'center'})
        )

    for cls in classes:
        dff = df[(df['Boss'] == selected_boss) & (df['Class'] == cls)]

        if dff.empty:
            continue

        max_dps_df = dff.sort_values('DPS', ascending=False).groupby('Player', as_index=False).first()

        max_dps_with_tag = []
        for _, row in max_dps_df.iterrows():
            player_rows = dff[dff['Player'] == row['Player']].sort_values('Timestamp')
            is_new = row['DPS'] == player_rows.iloc[-1]['DPS']

            if is_new:
                player_name = f"{row['Player']} **🔥 (new!)**"
            else:
                player_name = row['Player']

            max_dps_with_tag.append({'Player': player_name, 'DPS': row['DPS']})

        final_df = pd.DataFrame(max_dps_with_tag)
        final_df['Rank'] = final_df['DPS'].rank(ascending=False, method='first').astype(int)
        final_df = final_df.sort_values('DPS', ascending=False)[['Rank', 'Player', 'DPS']]

        tables.append(build_table(cls, final_df))
        all_players.extend(final_df['Player'].str.replace(" **🔥 (new!)**", "", regex=False).tolist())

    latest_time = df[df['Boss'] == selected_boss]['Timestamp'].max()
    last_update_str = f"Last update: {latest_time.strftime('%b %d, %Y – %H:%M')}"
    player_options = [{'label': p, 'value': p} for p in sorted(set(all_players))]

    return tables, podium, last_update_str, player_options

# Player comparison plot
@app.callback(
    Output('comparison-plot', 'figure'),
    Input('player-filter', 'value'),
    Input('boss-filter', 'value')
)
def update_comparison_plot(selected_players, selected_boss):
    filtered_df = df[(df['Boss'] == selected_boss)]

    if selected_players:
        filtered_df = filtered_df[filtered_df['Player'].isin(selected_players)]

    fig = px.line(
        filtered_df,
        x='Timestamp',
        y='DPS',
        color='Player',
        markers=True,
        title='DPS Over Time Comparison'
    )
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(gridcolor='lightgray', title='Timestamp', tickformat='%b %d, %H:%M'),
        yaxis=dict(gridcolor='lightgray', title='DPS')
    )

    return fig

if __name__ == "__main__":
    app.run(debug=True)

