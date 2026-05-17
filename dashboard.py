import streamlit as st
import pandas as pd
import time
from datetime import datetime
import CoolProp.CoolProp as CP
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import json

# ==========================================
# 1. 页面基本配置
# ==========================================
st.set_page_config(page_title="Bertram Digital Twin", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 📡 2. 核心物联引擎：云端直连 EMQX MQTT (后台守护线程)
# ==========================================
MQTT_BROKER = "x77a33b7.ala.cn-hangzhou.emqxsl.cn"
MQTT_PORT = 8883
MQTT_TOPIC = "/testtopic"
MQTT_USER = "BBBB"
MQTT_PASS = "bbbbb"


@st.cache_resource
def start_mqtt_client():
    """使用 cache_resource 确保云端大屏只启动一次 MQTT 监听线程"""
    data_buffer = []

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0 or reason_code == "Success":
            client.subscribe(MQTT_TOPIC)
            print("✅ 云端大屏已成功接入 EMQX 神经网络!")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            sensors = payload.get("temperature", payload)
            if isinstance(sensors, dict):
                # 统一转大写，防止下位机大小写漂移
                sensors = {k.upper().strip(): float(v) for k, v in sensors.items() if
                           isinstance(v, (int, float, str)) and k != "TIME_STAMP"}
                sensors['TIME_STAMP'] = datetime.now()

                data_buffer.append(sensors)
                # 内存保护：云端仅保留最近 500 条数据用于波形渲染
                if len(data_buffer) > 500:
                    data_buffer.pop(0)
        except Exception as e:
            pass

    # 兼容不同版本的 paho-mqtt
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="streamlit_cloud_viewer_001")
    except AttributeError:
        client = mqtt.Client(client_id="streamlit_cloud_viewer_001")

    client.tls_set()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()  # 在后台线程启动监听，不阻塞网页

    return data_buffer


# 获取后台持续更新的数据池
sensor_data_pool = start_mqtt_client()

# ==========================================
# 🎨 3. 高级数字孪生 CSS 引擎
# ==========================================
st.markdown("""
<style>
    .stApp { background: radial-gradient(circle at center top, #0A1428 0%, #030712 100%); font-family: 'Segoe UI', sans-serif; }
    header {visibility: hidden;}
    .main-title { text-align: center; color: #E2E8F0; font-size: 34px; font-weight: 800; letter-spacing: 4px; text-shadow: 0 0 15px rgba(0, 216, 255, 0.6); margin-top: -40px; margin-bottom: 25px; }
    .dual-card { background: linear-gradient(180deg, rgba(16, 33, 65, 0.6) 0%, rgba(5, 12, 25, 0.8) 100%); border: 1px solid rgba(0, 216, 255, 0.25); border-radius: 10px; padding: 10px 8px; margin-bottom: 12px; box-shadow: inset 0 0 15px rgba(0, 216, 255, 0.03), 0 4px 10px rgba(0,0,0,0.5); transition: transform 0.2s; }
    .dc-title { color: #3399FF; font-size: 13px; font-weight: bold; margin-bottom: 5px; margin-left: 5px; text-transform: uppercase; text-shadow: 0 0 5px rgba(51, 153, 255, 0.4); }
    .dc-row { display: flex; justify-content: space-evenly; align-items: center; }
    .dc-item { text-align: center; flex: 1; }
    .dc-divider { width: 1px; height: 35px; background: rgba(0, 216, 255, 0.2); }
    .dc-label { color: #94A3B8; font-size: 11px; margin-bottom: 2px; }
    .dc-value { color: #00D8FF; font-size: 24px; font-weight: bold; text-shadow: 0 0 8px rgba(0, 216, 255, 0.4); }
    .dc-unit { font-size: 11px; color: #64748B; font-weight: normal; }
    .alert-matrix { display: flex; justify-content: space-between; gap: 10px; margin-top: 10px; }
    .alert-box { flex: 1; padding: 12px 5px; border-radius: 8px; text-align: center; background: rgba(10, 20, 40, 0.8); border: 1px solid; display: flex; flex-direction: column; align-items: center; }
    .alert-safe { border-color: rgba(16, 185, 129, 0.3); }
    .alert-danger { border-color: rgba(239, 68, 68, 0.8); background: rgba(239, 68, 68, 0.1); }
    .alert-warn { border-color: rgba(245, 158, 11, 0.8); }
    .led-bulb { width: 16px; height: 16px; border-radius: 50%; margin-bottom: 8px; }
    .led-green { background-color: #10B981; box-shadow: 0 0 10px #10B981, inset 0 0 5px rgba(255,255,255,0.5); }
    .led-yellow { background-color: #F59E0B; box-shadow: 0 0 15px #F59E0B; animation: pulse-yellow 1.5s infinite; }
    .led-red { background-color: #EF4444; box-shadow: 0 0 15px #EF4444; animation: pulse-red 0.8s infinite; }
    @keyframes pulse-red { 0% { box-shadow: 0 0 10px #EF4444; } 50% { box-shadow: 0 0 25px #EF4444; } 100% { box-shadow: 0 0 10px #EF4444; } }
    @keyframes pulse-yellow { 0% { box-shadow: 0 0 10px #F59E0B; } 50% { box-shadow: 0 0 20px #F59E0B; } 100% { box-shadow: 0 0 10px #F59E0B; } }
    .alert-title { color: #E2E8F0; font-size: 12px; margin-top: 2px; }
    .alert-val { font-size: 15px; font-weight: bold; margin-top: 2px; }
    hr { border-top: 1px solid rgba(0, 216, 255, 0.15); margin: 15px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>⚡ BERTRAM 数字化孪生控制大屏</div>", unsafe_allow_html=True)

# ==========================================
# ⚙️ 4. 系统物理配置与辅助函数
# ==========================================
REFRIGERANT = 'R134a'
VOLTAGE = 220.0
POWER_FACTOR = 0.85
HIGH_POUT_LIMIT, LOW_PIN_LIMIT, LOW_SH_LIMIT, HIGH_TCOMO_LIMIT = 16.0, 0.5, 2.0, 95.0


def calculate_thermodynamics(row):
    try:
        pin_abs = (float(row.get('PIN', 0)) + 1.01325) * 100000.0
        pout_abs = (float(row.get('POUT', 0)) + 1.01325) * 100000.0
        tcomi_k = float(row.get('TCOMI', 0)) + 273.15
        tcomo_k = float(row.get('TCOMO', 0)) + 273.15
        outcono_k = float(row.get('OUTCONO', 0)) + 273.15

        tsat_in_k = CP.PropsSI('T', 'P', pin_abs, 'Q', 1, REFRIGERANT)
        tsat_out_k = CP.PropsSI('T', 'P', pout_abs, 'Q', 1, REFRIGERANT)
        sh = (tcomi_k - 273.15) - (tsat_in_k - 273.15)
        dsh = (tcomo_k - 273.15) - (tsat_out_k - 273.15)

        h1 = CP.PropsSI('H', 'P', pin_abs, 'T', tcomi_k, REFRIGERANT)
        h2 = CP.PropsSI('H', 'P', pout_abs, 'T', tcomo_k, REFRIGERANT)
        h3 = CP.PropsSI('H', 'P', pout_abs, 'T', outcono_k, REFRIGERANT)

        cop = (h2 - h3) / (h2 - h1) if (h2 - h1) > 0 else 0.0
        return pd.Series({'SH': sh, 'DSH': dsh, 'COP': cop})
    except:
        return pd.Series({'SH': 0.0, 'DSH': 0.0, 'COP': 0.0})


def dual_card(title, l1, v1, u1, l2, v2, u2):
    return f"""<div class="dual-card"><div class="dc-title">◈ {title}</div><div class="dc-row"><div class="dc-item"><div class="dc-label">{l1}</div><div class="dc-value">{v1} <span class="dc-unit">{u1}</span></div></div><div class="dc-divider"></div><div class="dc-item"><div class="dc-label">{l2}</div><div class="dc-value">{v2} <span class="dc-unit">{u2}</span></div></div></div></div>"""


def create_gauge(value, title, max_val, color, suffix=""):
    fig = go.Figure(
        go.Indicator(mode="gauge+number", value=value, number={'suffix': suffix, 'font': {'color': color, 'size': 24}},
                     title={'text': title, 'font': {'color': '#3399FF', 'size': 13}}, gauge={
                'axis': {'range': [None, max_val], 'tickwidth': 1, 'tickcolor': "#3399FF",
                         'tickfont': {'color': '#94A3B8'}}, 'bar': {'color': color}, 'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 1, 'bordercolor': "rgba(0, 216, 255, 0.2)",
                'steps': [{'range': [0, max_val], 'color': "rgba(10, 20, 40, 0.6)"}]}))
    fig.update_layout(height=170, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      font={'color': "#00D8FF"})
    return fig


def create_tech_line_chart(plot_df, title, y_title=""):
    fig = go.Figure()
    colors, fills = ['#00D8FF', '#F59E0B', '#10B981', '#C084FC', '#FB7185'], ['rgba(0,216,255,0.1)',
                                                                              'rgba(245,158,11,0.1)',
                                                                              'rgba(16,185,129,0.1)',
                                                                              'rgba(192,132,252,0.1)',
                                                                              'rgba(251,113,133,0.1)']
    for i, col in enumerate(plot_df.columns):
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[col], mode='lines', name=col,
                                 line=dict(width=2.5, color=colors[i % len(colors)], shape='spline'), fill='tozeroy',
                                 fillcolor=fills[i % len(fills)], hoverinfo='x+y+name'))
    fig.update_layout(title=dict(text=f"◈ {title}", font=dict(color='#E2E8F0', size=15)), paper_bgcolor='rgba(0,0,0,0)',
                      plot_bgcolor='rgba(10,20,40,0.5)', font=dict(color='#94A3B8', size=11),
                      xaxis=dict(showgrid=True, gridcolor='rgba(0, 216, 255, 0.1)', zeroline=False,
                                 tickformat="%H:%M:%S"),
                      yaxis=dict(title=y_title, showgrid=True, gridcolor='rgba(0, 216, 255, 0.1)', zeroline=False),
                      margin=dict(l=30, r=20, t=40, b=10),
                      legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5,
                                  font=dict(color='#E2E8F0')), hovermode="x unified", height=280)
    return fig


# ==========================================
# 📊 5. 数据流处理与界面渲染
# ==========================================
if len(sensor_data_pool) == 0:
    st.info("📡 正在连接 EMQX 杭州节点... 等待底层试验台推送首帧 MQTT 数据流...")
else:
    df = pd.DataFrame(sensor_data_pool)
    df.set_index('TIME_STAMP', inplace=True)
    latest = df.iloc[-1]

    pout, pin, tcomo, ysjdl = latest.get('POUT', 0), latest.get('PIN', 0), latest.get('TCOMO', 0), latest.get('YSJDL',
                                                                                                              0)
    zkbdl = latest.get('ZKBDL', 0)

    w_comp = ysjdl * VOLTAGE * POWER_FACTOR / 1000.0
    w_vp = zkbdl * VOLTAGE * POWER_FACTOR / 1000.0
    w_total = w_comp + w_vp

    thermo_data = calculate_thermodynamics(latest)
    sh, dsh, cop = thermo_data['SH'], thermo_data['DSH'], thermo_data['COP']
    t_avg = (float(latest.get('T1', 0)) + float(latest.get('T2', 0)) + float(latest.get('T3', 0))) / 3.0
    w_avg = (float(latest.get('W1', 0)) + float(latest.get('W2', 0)) + float(latest.get('W3', 0))) / 3.0

    col_left, col_center, col_right = st.columns([1.1, 2.5, 1.1])

    with col_left:
        st.markdown(
            dual_card("压缩机吸排气压力", "吸气 (PIN)", f"{pin:.2f}", "bar", "排气 (POUT)", f"{pout:.2f}", "bar"),
            unsafe_allow_html=True)
        st.markdown(
            dual_card("运行回路监测电流", "压缩机 (YSJDL)", f"{ysjdl:.2f}", "A", "真空泵 (ZKBDL)", f"{zkbdl:.2f}", "A"),
            unsafe_allow_html=True)
        st.markdown(
            dual_card("设备实时运行能耗", "压缩机能耗", f"{w_comp:.2f}", "kW", "真空泵能耗", f"{w_vp:.2f}", "kW"),
            unsafe_allow_html=True)
        st.markdown(dual_card("系统综合能效评估", "系统总功耗", f"{w_total:.2f}", "kW", "热力学 COP", f"{cop:.2f}", ""),
                    unsafe_allow_html=True)
        st.markdown(
            dual_card("系统进排气过热度", "吸气过热 (SH)", f"{sh:.1f}", "℃", "排气过热 (DSH)", f"{dsh:.1f}", "℃"),
            unsafe_allow_html=True)
        st.markdown(
            dual_card("靶材物料与环境状态", "当前重量 (ZL)", f"{latest.get('ZL', 0):.1f}", "g", "平均湿度 (W_AVG)",
                      f"{w_avg:.1f}", "%"), unsafe_allow_html=True)

    with col_center:
        st.markdown(
            """<div style="background: rgba(10, 20, 40, 0.4); border: 1px solid rgba(0, 216, 255, 0.15); border-radius: 12px; height: 380px; padding: 20px; text-align: center; display: flex; flex-direction: column; justify-content: center; position: relative; margin-bottom: 5px;"><h3 style="color: rgba(51, 153, 255, 0.3);">[ 3D 设 备 孪生 图 纸 预 留 区 ]</h3></div>""",
            unsafe_allow_html=True)
        cg1, cg2 = st.columns(2)
        with cg1: st.plotly_chart(create_gauge(latest.get('ZKD', 0), "绝对真空度 (ZKD)", 120000, "#00D8FF", " Pa"),
                                  width="stretch")
        with cg2: st.plotly_chart(create_gauge(latest.get('PZFKD', 0), "EEV 开度 (PZFKD)", 100, "#22D3EE", " %"),
                                  width="stretch")

        pout_cls, pout_led = ("alert-danger", "led-red") if pout > HIGH_POUT_LIMIT else ("alert-safe", "led-green")
        pin_cls, pin_led = ("alert-danger", "led-red") if pin < LOW_PIN_LIMIT else ("alert-safe", "led-green")
        sh_cls, sh_led = ("alert-warn", "led-yellow") if (sh < LOW_SH_LIMIT and ysjdl > 1.0) else (
        "alert-safe", "led-green")
        tcomo_cls, tcomo_led = ("alert-danger", "led-red") if tcomo > HIGH_TCOMO_LIMIT else ("alert-safe", "led-green")

        st.markdown(
            f"""<div class="alert-matrix"><div class="alert-box {pout_cls}"><div class="led-bulb {pout_led}"></div><div class="alert-title">高压排气</div><div class="alert-val" style="color: {'#EF4444' if pout > HIGH_POUT_LIMIT else '#10B981'};">{pout:.2f} bar</div></div><div class="alert-box {pin_cls}"><div class="led-bulb {pin_led}"></div><div class="alert-title">低压吸气</div><div class="alert-val" style="color: {'#EF4444' if pin < LOW_PIN_LIMIT else '#10B981'};">{pin:.2f} bar</div></div><div class="alert-box {sh_cls}"><div class="led-bulb {sh_led}"></div><div class="alert-title">液击风险(SH)</div><div class="alert-val" style="color: {'#F59E0B' if (sh < LOW_SH_LIMIT and ysjdl > 1.0) else '#10B981'};">{sh:.1f} ℃</div></div><div class="alert-box {tcomo_cls}"><div class="led-bulb {tcomo_led}"></div><div class="alert-title">排气超温</div><div class="alert-val" style="color: {'#EF4444' if tcomo > HIGH_TCOMO_LIMIT else '#10B981'};">{tcomo:.1f} ℃</div></div></div>""",
            unsafe_allow_html=True)

    with col_right:
        st.markdown(dual_card("压缩机进出口温度", "进口 (TCOMI)", f"{latest.get('TCOMI', 0):.1f}", "℃", "出口 (TCOMO)",
                              f"{tcomo:.1f}", "℃"), unsafe_allow_html=True)
        st.markdown(
            dual_card("蒸发器进出口温度", "进口 (EVPINT)", f"{latest.get('EVPINT', 0):.1f}", "℃", "出口 (EVPOUT)",
                      f"{latest.get('EVPOUT', 0):.1f}", "℃"), unsafe_allow_html=True)
        st.markdown(dual_card("冷凝器进出口温度", "进口 (CONIN)", f"{latest.get('CONIN', 0):.1f}", "℃", "出口 (CONOUT)",
                              f"{latest.get('CONOUT', 0):.1f}", "℃"), unsafe_allow_html=True)
        st.markdown(dual_card("外冷出与靶材核心", "外冷出 (OUTCONO)", f"{latest.get('OUTCONO', 0):.1f}", "℃",
                              "靶材温 (WULIAOT)", f"{latest.get('WULIAOT', 0):.1f}", "℃"), unsafe_allow_html=True)
        st.markdown(dual_card("腔体多点平均温度", "平均测温 (T_AVG)", f"{t_avg:.1f}", "℃", "系统工质", REFRIGERANT, ""),
                    unsafe_allow_html=True)
        st.markdown(dual_card("数字孪生通信网络", "协议节点", "EMQX", "", "传输状态", "实时同步", ""),
                    unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #00D8FF;'>📉 深度时序波形诊断与滤波网络</h4>", unsafe_allow_html=True)

    plot_df = df.copy()
    if 'YSJDL' in plot_df.columns: plot_df['YSJDL'] = plot_df['YSJDL'].rolling(window=10, min_periods=1).mean().round(2)
    if 'ZKBDL' in plot_df.columns: plot_df['ZKBDL'] = plot_df['ZKBDL'].rolling(window=10, min_periods=1).mean().round(2)
    plot_df['系统总功耗(kW)'] = (plot_df['YSJDL'] + plot_df['ZKBDL']) * VOLTAGE * POWER_FACTOR / 1000.0
    thermo_history = plot_df.apply(calculate_thermodynamics, axis=1)
    plot_df['系统COP'] = thermo_history['COP']

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        keys = [k for k in ['POUT', 'PIN'] if k in plot_df.columns]
        if keys: st.plotly_chart(create_tech_line_chart(plot_df[keys], "系统高低压动态极值", "压力 (bar)"),
                                 width="stretch")
    with col_c2:
        keys = [k for k in ['CONIN', 'CONOUT', 'WULIAOT'] if k in plot_df.columns]
        if keys: st.plotly_chart(create_tech_line_chart(plot_df[keys], "换热侧与物料温升逼近", "温度 (℃)"),
                                 width="stretch")
    with col_c3:
        keys = [k for k in ['系统总功耗(kW)', '系统COP'] if k in plot_df.columns]
        if keys: st.plotly_chart(create_tech_line_chart(plot_df[keys], "能效与功耗动态时序交叉", "数值"),
                                 width="stretch")

# 心跳刷新，实现网页每2秒抓取一次最新数据重绘
time.sleep(2)
st.rerun()