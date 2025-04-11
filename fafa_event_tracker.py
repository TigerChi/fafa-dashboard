
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
from dash import dash_table
import os

# 讀取資料並加上是否睡眠中標記
df = pd.read_csv("fafa_data.csv", parse_dates=["開始時間"])
df['時間（小時）'] = df['開始時間'].dt.hour + df['開始時間'].dt.minute / 60
df['日期'] = df['開始時間'].dt.date

# 判斷是否為睡眠中癲癇（關鍵字比對）
sleep_keywords = ['午睡', '睡覺', '夜間', '睡夢', '入睡', '叫醒', '清晨', '睡中', '躺著']
df['描述'] = df['描述'].fillna("")
df['是否睡眠中'] = df.apply(
    lambda row: True if row['項目'] == '癲癇' and any(kw in row['描述'] for kw in sleep_keywords)
    else False, axis=1
)

# App 初始化
app = Dash(__name__)

event_options = [{'label': etype, 'value': etype} for etype in sorted(df['項目'].unique())]
chart_modes = [
    {'label': '每日癲癇次數（含標記）', 'value': 'bar_count'},
    {'label': '每日癲癇總秒數（含標記）', 'value': 'bar_duration'}
]
sleep_filter_options = [
    {'label': '全部', 'value': 'all'},
    {'label': '僅睡眠中癲癇', 'value': 'sleep'},
    {'label': '僅非睡眠中癲癇', 'value': 'awake'}
]

app.layout = html.Div([
    html.H2("發發癲癇記錄圖表（睡眠狀態分類）"),
    html.Label("選擇日期區間"),
    dcc.DatePickerRange(
        id='date-range',
        min_date_allowed=df['開始時間'].min().date(),
        max_date_allowed=df['開始時間'].max().date(),
        start_date=df['開始時間'].min().date(),
        end_date=df['開始時間'].max().date()
    ),
    html.Br(),
    html.Label("圖表模式"),
    dcc.Dropdown(
        id='chart-mode',
        options=chart_modes,
        value='bar_count',
        clearable=False
    ),
    html.Label("顯示類型"),
    dcc.Dropdown(
        id='sleep-filter',
        options=sleep_filter_options,
        value='all',
        clearable=False
    ),
    dcc.Graph(id='event-graph'),
    html.H4(id='detail-title'),
    dash_table.DataTable(
        id='detail-table',
        columns=[
            {'name': '開始時間', 'id': '開始時間'},
            {'name': '記錄值（秒）', 'id': '記錄值'},
            {'name': '描述', 'id': '描述'}
        ],
        data=[],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'fontWeight': 'bold'},
    )
])

@app.callback(
    Output('event-graph', 'figure'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input('chart-mode', 'value'),
    Input('sleep-filter', 'value')
)
def update_graph(start_date, end_date, chart_mode, sleep_filter):
    epilepsy_df = df[df['項目'] == '癲癇']
    epilepsy_df = epilepsy_df[
        (epilepsy_df['開始時間'].dt.date >= pd.to_datetime(start_date).date()) &
        (epilepsy_df['開始時間'].dt.date <= pd.to_datetime(end_date).date())
    ]

    if sleep_filter == 'sleep':
        epilepsy_df = epilepsy_df[epilepsy_df['是否睡眠中']]
    elif sleep_filter == 'awake':
        epilepsy_df = epilepsy_df[~epilepsy_df['是否睡眠中']]

    if chart_mode == 'bar_count':
        agg_df = epilepsy_df.groupby(
            [epilepsy_df['開始時間'].dt.date, epilepsy_df['是否睡眠中']]
        ).size().reset_index(name='癲癇次數')
        title = '每日癲癇次數（睡眠狀態分類）'
        y_label = '癲癇次數'
    else:
        epilepsy_df['記錄值'] = pd.to_numeric(epilepsy_df['記錄值'], errors='coerce')
        agg_df = epilepsy_df.groupby(
            [epilepsy_df['開始時間'].dt.date, epilepsy_df['是否睡眠中']]
        )['記錄值'].sum().reset_index(name='總秒數')
        title = '每日癲癇總秒數（睡眠狀態分類）'
        y_label = '總秒數'

    fig = px.bar(
        agg_df,
        x='開始時間',
        y=y_label,
        color='是否睡眠中',
        color_discrete_map={True: 'blue', False: 'red'},
        barmode='stack',
        title=title
    )
    fig.update_layout(height=700)
    return fig

@app.callback(
    Output('detail-title', 'children'),
    Output('detail-table', 'data'),
    Input('event-graph', 'clickData'),
    State('sleep-filter', 'value'),
    State('chart-mode', 'value')
)
def display_click_details(clickData, sleep_filter, chart_mode):
    if clickData is None:
        return "", []

    clicked_date = clickData['points'][0]['x']
    clicked_date = pd.to_datetime(clicked_date).date()
    detail_df = df[(df['項目'] == '癲癇') & (df['開始時間'].dt.date == clicked_date)]

    if sleep_filter == 'sleep':
        detail_df = detail_df[detail_df['是否睡眠中']]
    elif sleep_filter == 'awake':
        detail_df = detail_df[~detail_df['是否睡眠中']]

    detail_df = detail_df.sort_values('開始時間')
    table_data = detail_df[['開始時間', '記錄值', '描述']].copy()
    table_data['開始時間'] = table_data['開始時間'].astype(str)
    return f"{clicked_date} 癲癇詳細記錄", table_data.to_dict('records')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
