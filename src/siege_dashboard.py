import pandas as pd
import os
import typing_extensions
import dash
from dash import dcc, html, Input, Output, dash_table, State, ctx
import plotly.express as px
import dash_bootstrap_components as dbc

# Read the current siege data
df = pd.read_csv("Siege_Data.csv")
df["Datetime"] = pd.to_datetime(df["Timestamp"], format = "%y%m%d_%H%M") 
df['DPS'] = pd.to_numeric(df['DPS'], errors='coerce')


# Get unique bosses and classes
# Bosses and classes
bosses = sorted(df['Boss'].unique())
classes = sorted(df['Class'].dropna().unique())

# App setup
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Siege DPS Dashboard"

# Layout
app.layout = html.Div([
    html.H2("Siege DPS Dashboard"),
    #html.P("by Cruellia", style={'fontSize': '0.9rem', 'color': 'gray', 'marginTop': '-0.5rem', 'marginBottom': '1rem'}),
        html.Div([
    html.P("by Cruellia", style={
        'fontSize': '0.9rem',
        'color': 'gray',
        'marginTop': '-0.5rem',
        'marginBottom': '0.2rem'
    }),
    html.P(f"Last update: {df['Datetime'].max().strftime('%b %d, %Y %H:%M')}", style={
        'fontSize': '0.85rem',
        'color': 'gray',
        'marginBottom': '1.5rem'
        })
    ]),

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
        ], width=6),

        dbc.Col([
            html.Div(id='dps-over-time', style={
                'display': 'flex',
                'flexDirection': 'column',
                'height': '650vh',
                'maxHeight': '6000px',
                'minHeight': '800px',
                'overflowY': 'auto',
                'border': '1px solid #ddd',
                'padding': '1rem'
            })
        ], width=6),
    ])
])

# Utility to build per-class tables
def build_table(class_name, dff_class):
    return html.Div([
        html.H5(class_name),

        dash_table.DataTable(
            id={'type': 'dps-table', 'index': class_name},
            columns=[
                {'name': 'Rank', 'id': 'Rank'},
                {'name': 'Player', 'id': 'Player', 'presentation': 'markdown'},
                {'name': 'DPS', 'id': 'DPS', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            ],
            data=dff_class.to_dict('records'),
            row_selectable='single',
            selected_rows=[0],
            style_cell={'textAlign': 'left'},
            style_table={'overflowX': 'auto'},
            page_size=10,
            cell_selectable=True
        )
    ], style={'marginBottom': '2rem'})

# Create tables for each class
@app.callback(
    Output('class-tables', 'children'),
    Input('boss-filter', 'value')
)
def update_all_class_tables(selected_boss):
    tables = []

    for cls in classes:
        dff = df[(df['Boss'] == selected_boss) & (df['Class'] == cls)]

        if dff.empty:
            continue

        # Max DPS per player
        max_dps_df = dff.sort_values('DPS', ascending=False).groupby('Player', as_index=False).first()

        # Annotate if latest DPS is their highest
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

    return tables

# Handle DPS over time plots on click
@app.callback(
    Output('dps-over-time', 'children'),
    Input({'type': 'dps-table', 'index': dash.ALL}, 'selected_rows'),
    State({'type': 'dps-table', 'index': dash.ALL}, 'data'),
    State({'type': 'dps-table', 'index': dash.ALL}, 'id'),
    State('boss-filter', 'value')
)
def update_dps_charts_click(selected_rows_all, all_table_data, all_table_ids, selected_boss):
    charts = []

    for i, table_data in enumerate(all_table_data):
        if not table_data:
            continue

        selected_rows = selected_rows_all[i] if selected_rows_all[i] else [0]
        if not selected_rows:
            continue

        row_idx = selected_rows[0]
        player_name = table_data[row_idx]['Player'].replace(" **🔥 (new!)**", "")
        cls = all_table_ids[i]['index']

        player_df = df[(df['Boss'] == selected_boss) & (df['Player'] == player_name)].sort_values('Timestamp')

        if player_df.empty:
            continue

        fig = px.line(
            player_df,
            x='Timestamp',
            y='DPS',
            title=f'{player_name} – DPS Over Time ({cls})',
            markers=True
        )
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(gridcolor='lightgray', title='Timestamp', tickformat='%b %d, %H:%M'),
            yaxis=dict(gridcolor='lightgray', title='DPS')
        )

        #charts.append(dcc.Graph(figure=fig))
        charts.append(
            html.Div(
                dcc.Graph(figure=fig),
                style={'marginBottom': '5.3rem'}
            )
        )

    return charts

if __name__ == "__main__":
    app.run(debug=True)
