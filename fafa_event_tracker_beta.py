
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
from dash import dash_table
import os


# 讀取資料，請確保是乾淨版本
df = pd.read_csv("fafa_data.csv")

# 明確轉換成 datetime，才能使用 .dt
df['開始時間'] = pd.to_datetime(df['開始時間'], errors='coerce')
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

chart_modes = [
    {'label': '每日癲癇次數（含標記）', 'value': 'bar_count'},
    {'label': '每日癲癇總秒數（含標記）', 'value': 'bar_duration'}
]

app.layout = html.Div([
    html.H2("發發癲癇記錄圖表（睡眠分類 + S101 + 藥量調整）"),
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
    Input('chart-mode', 'value')
)
def update_graph(start_date, end_date, chart_mode):
    epilepsy_df = df[df['項目'] == '癲癇']
    epilepsy_df = epilepsy_df[
        (epilepsy_df['開始時間'].dt.date >= pd.to_datetime(start_date).date()) &
        (epilepsy_df['開始時間'].dt.date <= pd.to_datetime(end_date).date())
    ]

    if chart_mode == 'bar_count':
        agg_df = epilepsy_df.groupby(
            [epilepsy_df['開始時間'].dt.date, epilepsy_df['是否睡眠中']]
        ).size().reset_index(name='癲癇次數')
        title = '每日癲癇次數（睡眠分類 + S101 + 藥量調整）'
        y_label = '癲癇次數'
    else:
        epilepsy_df['記錄值'] = pd.to_numeric(epilepsy_df['記錄值'], errors='coerce')
        agg_df = epilepsy_df.groupby(
            [epilepsy_df['開始時間'].dt.date, epilepsy_df['是否睡眠中']]
        )['記錄值'].sum().reset_index(name='總秒數')
        title = '每日癲癇總秒數（睡眠分類 + S101 + 藥量調整）'
        y_label = '總秒數'

    # 長條圖（睡眠分類）
    fig = px.bar(
        agg_df,
        x='開始時間',
        y=y_label,
        color='是否睡眠中',
        color_discrete_map={True: 'blue', False: 'red'},
        barmode='stack',
        title=title
    )

    # 加入 S101 與藥量調整標記
    for label, symbol, color in [('S101', 'circle', 'blue'), ('藥量調整', 'diamond', 'green')]:
        mark_df = df[df['項目'] == label]
        mark_df = mark_df[
            (mark_df['開始時間'].dt.date >= pd.to_datetime(start_date).date()) &
            (mark_df['開始時間'].dt.date <= pd.to_datetime(end_date).date())
        ]
        fig.add_trace(go.Scatter(
            x=mark_df['開始時間'].dt.date,
            y=[0] * len(mark_df),
            mode='markers',
            name=label,
            marker=dict(symbol=symbol, size=12, color=color),
            hovertext=mark_df['描述']
        ))

    fig.update_layout(height=700)
    return fig

@app.callback(
    Output('detail-title', 'children'),
    Output('detail-table', 'data'),
    Input('event-graph', 'clickData'),
    State('chart-mode', 'value')
)
def display_click_details(clickData, chart_mode):
    if clickData is None:
        return "", []

    clicked_date = clickData['points'][0]['x']
    clicked_date = pd.to_datetime(clicked_date).date()
    detail_df = df[(df['項目'] == '癲癇') & (df['開始時間'].dt.date == clicked_date)]

    detail_df = detail_df.sort_values('開始時間')
    table_data = detail_df[['開始時間', '記錄值', '描述']].copy()
    table_data['開始時間'] = table_data['開始時間'].astype(str)
    return f"{clicked_date} 癲癇詳細記錄", table_data.to_dict('records')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
