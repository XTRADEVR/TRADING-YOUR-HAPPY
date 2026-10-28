"""
Forex Risk Management Calculator & Currency Strength Meter
Framework: Streamlit
Perintah menjalankan: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import datetime

# -----------------------------------------------------------------------------
# 1. Konfigurasi Halaman & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Forex Risk & Strength Dashboard",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling untuk merapikan kartu metrik
st.markdown("""
<style>
    .main-header { font-size: 2.1rem; font-weight: 700; color: #1E293B; }
    .stMetric { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Data Pasangan Mata Uang & Referensi Pasar (Bisa diintegrasikan yfinance)
# -----------------------------------------------------------------------------
PAIR_DATA = {
    "EUR/USD": {"rate": 1.0845, "pip_dec": 4, "spread": 0.8, "base": "EUR", "quote": "USD", "change_24h": +0.35},
    "GBP/USD": {"rate": 1.2980, "pip_dec": 4, "spread": 1.1, "base": "GBP", "quote": "USD", "change_24h": -0.18},
    "USD/JPY": {"rate": 153.25, "pip_dec": 2, "spread": 0.9, "base": "USD", "quote": "JPY", "change_24h": +0.52},
    "USD/CHF": {"rate": 0.8670, "pip_dec": 4, "spread": 1.2, "base": "USD", "quote": "CHF", "change_24h": -0.25},
    "USD/CAD": {"rate": 1.3890, "pip_dec": 4, "spread": 1.3, "base": "USD", "quote": "CAD", "change_24h": +0.12},
    "AUD/USD": {"rate": 0.6575, "pip_dec": 4, "spread": 1.0, "base": "AUD", "quote": "USD", "change_24h": -0.42},
    "NZD/USD": {"rate": 0.5960, "pip_dec": 4, "spread": 1.4, "base": "NZD", "quote": "USD", "change_24h": -0.38},
    "EUR/GBP": {"rate": 0.8355, "pip_dec": 4, "spread": 1.2, "base": "EUR", "quote": "GBP", "change_24h": +0.45},
    "EUR/JPY": {"rate": 166.20, "pip_dec": 2, "spread": 1.5, "base": "EUR", "quote": "JPY", "change_24h": +0.82},
    "GBP/JPY": {"rate": 198.90, "pip_dec": 2, "spread": 1.8, "base": "GBP", "quote": "JPY", "change_24h": +0.34},
}

# -----------------------------------------------------------------------------
# 3. Logika Perhitungan Nilai Pip & Ukuran Lot (Standard, Mini, Micro)
# -----------------------------------------------------------------------------
def calculate_pip_value(pair: str, rate: float) -> float:
    """Menghitung nilai 1 pip per Standard Lot (100,000 unit) dalam USD."""
    meta = PAIR_DATA.get(pair, {"pip_dec": 4, "quote": "USD", "base": "EUR"})
    pip_size = 10 ** (-meta["pip_dec"])
    lot_units = 100_000

    if meta["quote"] == "USD":
        return pip_size * lot_units  # $10.00 untuk EUR/USD, GBP/USD, AUD/USD
    elif meta["base"] == "USD":
        return (pip_size * lot_units) / rate  # USD/JPY, USD/CHF, USD/CAD
    elif meta["quote"] == "JPY":
        usd_jpy_rate = PAIR_DATA["USD/JPY"]["rate"]
        return (pip_size * lot_units) / usd_jpy_rate
    elif meta["quote"] == "GBP":
        gbp_usd_rate = PAIR_DATA["GBP/USD"]["rate"]
        return (pip_size * lot_units) * gbp_usd_rate
    return 10.0

def calculate_lot_size(balance: float, risk_pct: float, sl_pips: float, pip_value: float):
    """Menghitung batas risiko uang dan ukuran lot."""
    risk_amount = balance * (risk_pct / 100.0)
    if sl_pips <= 0 or pip_value <= 0:
        return 0.0, 0.0, 0.0, 0.0, risk_amount
    
    # Formula Matematika: Lot = Risiko Uang / (Stop Loss pips * Nilai Pip Standar)
    standard_lots = risk_amount / (sl_pips * pip_value)
    mini_lots = standard_lots * 10
    micro_lots = standard_lots * 100
    units = standard_lots * 100_000
    return standard_lots, mini_lots, micro_lots, units, risk_amount

# -----------------------------------------------------------------------------
# 4. Sidebar Input Parameter (st.sidebar)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Parameter Trading")
    st.caption("Atur parameter saldo dan toleransi risiko Anda")
    
    selected_pair = st.selectbox("Pilih Pasangan Mata Uang (Pair)", list(PAIR_DATA.keys()))
    account_currency = st.selectbox("Mata Uang Akun", ["USD", "EUR", "GBP", "IDR"], index=0)
    
    account_balance = st.number_input(
        f"Saldo Akun ({account_currency})",
        min_value=10.0,
        max_value=10_000_000.0,
        value=10_000.0,
        step=500.0
    )
    
    risk_percent = st.slider(
        "Persentase Risiko per Trade (%)",
        min_value=0.1,
        max_value=5.0,
        value=1.0,
        step=0.1,
        help="Rekomendasi institusi: 1% - 2% modal per trade."
    )
    
    stop_loss_pips = st.number_input(
        "Jarak Stop Loss (Pips)",
        min_value=1.0,
        max_value=300.0,
        value=25.0,
        step=1.0
    )
    
    rr_ratio = st.slider(
        "Target Risk to Reward (R:R)",
        min_value=1.0,
        max_value=5.0,
        value=2.0,
        step=0.5
    )
    
    leverage = st.selectbox("Leverage Akun", ["1:50", "1:100", "1:200", "1:500"], index=1)
    st.divider()
    st.info("🛡️ Gunakan selalu Stop Loss untuk melindungi modal Anda.")

# -----------------------------------------------------------------------------
# 5. Kalkulasi Inti
# -----------------------------------------------------------------------------
current_rate = PAIR_DATA[selected_pair]["rate"]
pip_val = calculate_pip_value(selected_pair, current_rate)
std_lot, mini_lot, micro_lot, total_units, risk_cash = calculate_lot_size(
    account_balance, risk_percent, stop_loss_pips, pip_val
)
profit_target = risk_cash * rr_ratio
target_pips = stop_loss_pips * rr_ratio

# -----------------------------------------------------------------------------
# 6. Tampilan Dashboard Utama
# -----------------------------------------------------------------------------
st.title("Forex Risk Management & Currency Strength Meter")
st.markdown("Dashboard terintegrasi untuk menghitung posisi lot aman dan memantau momentum mata uang.")

tab1, tab2, tab3 = st.tabs([
    "📊 Kalkulator Lot Size",
    "⚡ Currency Strength Meter",
    "📈 Tren Pasangan Mata Uang"
])

# --- TAB 1: KALKULATOR LOT SIZE ---
with tab1:
    st.subheader(f"Hasil Kalkulasi Posisi: {selected_pair}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Maksimal Risiko Uang", f"${risk_cash:,.2f}", f"{risk_percent}% Saldo")
    with col2:
        st.metric("Rekomendasi Lot Standar", f"{std_lot:.2f} Lot", f"{total_units:,.0f} Units")
    with col3:
        st.metric("Nilai Pip / Lot Standar", f"${pip_val:.2f}", f"Rate: {current_rate}")
    with col4:
        st.metric(f"Potensi Profit (1:{rr_ratio:.1f})", f"${profit_target:,.2f}", f"+{target_pips:.0f} Pips Target")

    st.markdown("---")
    c_left, c_right = st.columns([1.2, 1])
    
    with c_left:
        st.markdown("#### 📦 Tabel Perbandingan Tipe Kontrak Lot (st.dataframe)")
        contract_data = {
            "Tipe Kontrak": ["Standard Lot (1.00)", "Mini Lot (0.10)", "Micro Lot (0.01)", "Nano Lot (0.001)"],
            "Ukuran Satuan (Units)": ["100,000", "10,000", "1,000", "100"],
            "Ukuran Lot Disarankan": [f"{std_lot:.2f} lot", f"{mini_lot:.2f} mini", f"{micro_lot:.2f} micro", f"{micro_lot * 10:.1f} nano"],
            "Total Risiko jika SL Kena": [f"${risk_cash:,.2f}", f"${risk_cash:,.2f}", f"${risk_cash:,.2f}", f"${risk_cash:,.2f}"]
        }
        st.dataframe(pd.DataFrame(contract_data), use_container_width=True, hide_index=True)

    with c_right:
        st.markdown("#### 📐 Logika & Rumus Matematika")
        st.latex(r"\text{Lot Standar} = \frac{\text{Saldo} \times (\text{Risiko \%} / 100)}{\text{Stop Loss (pips)} \times \text{Nilai Pip per Lot Standar}}")
        st.write(f"- Modal: **${account_balance:,.2f}**")
        st.write(f"- Risiko {risk_percent}%: **${risk_cash:,.2f}**")
        st.write(f"- Jarak SL: **{stop_loss_pips} pips**")
        st.write(f"- Hasil: **{std_lot:.2f} Standard Lot** ({micro_lot:.2f} Micro Lot)")

# --- TAB 2: CURRENCY STRENGTH METER ---
with tab2:
    st.subheader("⚡ Currency Strength Meter (Skala 0 - 10)")
    st.caption("Peringkat kekuatan 8 mata uang utama dunia:")
    
    currency_scores = {
        "USD": 7.8, "EUR": 6.9, "GBP": 5.4, "CHF": 5.1,
        "CAD": 4.6, "AUD": 3.8, "NZD": 3.2, "JPY": 1.9
    }
    
    col_str1, col_str2 = st.columns([1.4, 1])
    with col_str1:
        for curr, score in currency_scores.items():
            status = "🟢 Kuat" if score >= 6.8 else ("🔴 Lemah" if score <= 3.9 else "🟡 Netral")
            c1, c2 = st.columns([1, 3])
            with c1:
                st.write(f"**{curr}** ({status}) - `{score}/10`")
            with c2:
                st.progress(score / 10.0)
                
    with col_str2:
        st.markdown("#### 🎯 Rekomendasi Setup Probabilitas Tinggi")
        st.success("🟢 **BUY (Kuat vs Lemah):**\n- USD/JPY (USD 7.8 vs JPY 1.9)\n- EUR/JPY (EUR 6.9 vs JPY 1.9)")
        st.error("🔴 **SELL (Lemah vs Kuat):**\n- NZD/USD (NZD 3.2 vs USD 7.8)\n- AUD/USD (AUD 3.8 vs USD 7.8)")

# --- TAB 3: TREN PASANGAN MATA UANG ---
with tab3:
    st.subheader("📈 Tabel Pasar & Perubahan Harian (st.dataframe)")
    rows = []
    for pair, d in PAIR_DATA.items():
        rows.append({
            "Pair": pair,
            "Harga Terakhir": f"{d['rate']:.4f}" if d["pip_dec"] == 4 else f"{d['rate']:.2f}",
            "Spread (pips)": d["spread"],
            "Perubahan 24 Jam": f"{d['change_24h']:+.2f}%",
            "Sentimen": "Bullish 📈" if d["change_24h"] > 0 else "Bearish 📉"
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    
    st.markdown("#### 📊 Grafik Tren Harga 30 Hari Terakhir (st.line_chart)")
    np.random.seed(42)
    dates = pd.date_range(end=datetime.date.today(), periods=30)
    base_price = PAIR_DATA[selected_pair]["rate"]
    noise = np.cumsum(np.random.randn(30) * (base_price * 0.003))
    simulated_trend = base_price + noise
    chart_df = pd.DataFrame({"Tanggal": dates, f"Harga {selected_pair}": simulated_trend}).set_index("Tanggal")
    st.line_chart(chart_df)
