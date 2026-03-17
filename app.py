import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="BEN Project - Data Anak Analysis", layout="wide")

def process_data_anak(file):
    # Langsung tembak sheet '1. Data Anak' dan header di baris 11 (index 10)
    try:
        df = pd.read_excel(file, sheet_name='1. Data Anak', header=10)
    except Exception as e:
        st.error("Sheet '1. Data Anak' tidak ditemukan. Pastikan nama sheet sesuai.")
        return None
    
    # Cleaning: Ambil hanya baris yang memiliki Nama (Kolom B / Index 1)
    df = df.dropna(subset=[df.columns[1]])

    # Definisi kolom rujukan (J-P pola berulang setiap 7 kolom)
    # Kuartal 1: J-P (Index 9-15)
    # Kuartal 2: Q-W (Index 16-22)
    # Kuartal 3: X-AD (Index 23-29)
    # Kuartal 4: AE-AK (Index 30-36)
    q_indices = {
        'K1': list(range(9, 16)), 'K2': list(range(16, 23)),
        'K3': list(range(23, 30)), 'K4': list(range(30, 37))
    }
    
    cats = ['Kesehatan', 'Pendidikan', 'Mata Pencaharian', 'Sosial', 'Pemberdayaan', 'Ruj_Dalam', 'Ruj_Luar']

    processed = []
    for _, row in df.iterrows():
        # Data Dasar (B=1, C=2, D=3, G=6, I=8)
        info = {
            'Nama': str(row.iloc[1]),
            'Ragam': str(row.iloc[2]),
            'Diagnosa': str(row.iloc[3]),
            'Gender': 'Laki-laki' if str(row.iloc[6]).upper() == 'L' else 'Perempuan',
            'Usia': pd.to_numeric(row.iloc[8], errors='coerce'),
            'Ganda': 1 if "ganda" in str(row.iloc[2]).lower() else 0
        }
        
        # Kondisi Spesifik (Kebutuhan Point 5)
        d_val = str(info['Diagnosa']).lower()
        info['Cerebral Palsy'] = 1 if 'cerebral palsy' in d_val else 0
        info['Albinism'] = 1 if 'albinism' in d_val else 0
        info['Down Syndrome'] = 1 if 'down syndrome' in d_val else 0
        info['Kusta'] = 1 if 'kusta' in d_val else 0

        # Mapping Intervensi & Rujukan
        for q_tag, cols in q_indices.items():
            for i, cat in enumerate(cats):
                val = pd.to_numeric(row.iloc[cols[i]], errors='coerce')
                info[f"{q_tag}_{cat}"] = 1 if val == 1 else 0
        
        processed.append(info)

    res_df = pd.DataFrame(processed)
    
    # Pengelompokan Usia per 5 Tahun (Kebutuhan Point 1, 2, 3)
    bins = [0, 5, 10, 15, 20, 25, 100]
    labels = ['0-5 th', '6-10 th', '11-15 th', '16-20 th', '21-25 th', '26+ th']
    res_df['Kelompok Usia'] = pd.cut(res_df['Usia'], bins=bins, labels=labels)
    
    return res_df

# --- UI ---
st.title("📊 Monitoring Data Anak - Project BEN")

uploaded_file = st.file_uploader("Upload Annex 14", type=["xlsx"])

if uploaded_file:
    data = process_data_anak(uploaded_file)
    
    if data is not None:
        # Kalkulasi Kumulatif Tahunan (Pernah dapat di salah satu kuartal)
        main_cats = ['Kesehatan', 'Pendidikan', 'Mata Pencaharian', 'Sosial', 'Pemberdayaan']
        for c in main_cats + ['Ruj_Dalam', 'Ruj_Luar']:
            data[c] = data[[f"K{i}_{c}" for i in range(1, 5)]].max(axis=1)

        # TAMPILAN DASHBOARD
        st.divider()
        
        # Row 1: Intervensi per Usia & Total per Usia/Gender
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1. Intervensi per Kelompok Usia")
            m_data = data.melt(id_vars=['Kelompok Usia'], value_vars=main_cats)
            fig1 = px.bar(m_data.groupby(['Kelompok Usia', 'variable']).sum().reset_index(), 
                          x='Kelompok Usia', y='value', color='variable', barmode='group')
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            st.subheader("2. Total per Usia & Jenis Kelamin")
            fig2 = px.histogram(data, x='Kelompok Usia', color='Gender', barmode='group', text_auto=True)
            st.plotly_chart(fig2, use_container_width=True)

        # Row 2: Ganda & Ragam
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("3. Disabilitas Ganda per Usia & Gender")
            fig3 = px.bar(data[data['Ganda']==1].groupby(['Kelompok Usia', 'Gender']).size().reset_index(name='N'),
                          x='Kelompok Usia', y='N', color='Gender', barmode='group')
            st.plotly_chart(fig3, use_container_width=True)
        with c4:
            st.subheader("4. Ragam Disabilitas & Gender")
            fig4 = px.bar(data.groupby(['Ragam', 'Gender']).size().reset_index(name='N'),
                          x='N', y='Ragam', color='Gender', orientation='h')
            st.plotly_chart(fig4, use_container_width=True)

        # Row 3: Kondisi Spesifik & Rujukan
        st.divider()
        c5, c6, c7 = st.columns(3)
        with c5:
            st.subheader("5. Kondisi Spesifik")
            spec = data[['Cerebral Palsy', 'Albinism', 'Down Syndrome', 'Kusta']].sum().reset_index()
            st.table(spec.rename(columns={'index': 'Kondisi', 0: 'Jumlah'}))
        with c6:
            st.metric("6. Rujukan Dalam Kecamatan", int(data['Ruj_Dalam'].sum()))
        with c7:
            st.metric("7. Rujukan Luar Kecamatan", int(data['Ruj_Luar'].sum()))

        st.subheader("Data Mentah Terproses")
        st.dataframe(data)
