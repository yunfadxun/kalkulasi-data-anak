import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="BEN Project MEL Dashboard", layout="wide")

# --- FUNGSI PENGOLAHAN DATA ---
def load_and_process(file):
    # Membaca mulai header di Row 11 (index 10)
    df = pd.read_excel(file, sheet_name='1. Data Anak', header=10)
    
    # Cleaning: Ambil hanya baris yang ada namanya (Kolom B / index 1)
    df = df.dropna(subset=[df.columns[1]])
    
    # Mapping Indeks Kolom (0-indexed)
    # B:1, C:2, D:3, E:4, F:5, G:6, I:8
    # J-N: 9-13 (Intervensi Q1), O:14 (Internal), P:15 (Eksternal)
    # Pola berulang setiap 7 kolom
    
    q_map = {
        'Kuartal 1': list(range(9, 16)),
        'Kuartal 2': list(range(16, 23)),
        'Kuartal 3': list(range(23, 30)),
        'Kuartal 4': list(range(30, 37))
    }
    
    inter_names = ['Kesehatan', 'Pendidikan', 'Mata Pencaharian', 'Sosial', 'Pemberdayaan']
    ref_names = ['Rujukan Dalam', 'Rujukan Luar']
    all_cats = inter_names + ref_names

    processed_data = []
    
    for _, row in df.iterrows():
        # Data Dasar
        item = {
            'Nama': str(row.iloc[1]),
            'Ragam': str(row.iloc[2]),
            'Diagnosa': str(row.iloc[3]),
            'Gender': 'Laki-laki' if str(row.iloc[6]).upper() == 'L' else 'Perempuan',
            'Usia': pd.to_numeric(row.iloc[8], errors='coerce'),
            'Is_Ganda': 1 if "ganda" in str(row.iloc[2]).lower() else 0
        }
        
        # Cek Diagnosa Spesifik (CP, Albinism, Down Syndrome, Kusta)
        diag_clean = str(item['Diagnosa']).lower()
        item['CP'] = 1 if 'cerebral palsy' in diag_clean else 0
        item['Albinism'] = 1 if 'albinism' in diag_clean else 0
        item['Down Syndrome'] = 1 if 'down syndrome' in diag_clean else 0
        item['Kusta'] = 1 if 'kusta' in diag_clean else 0
        
        # Proses Intervensi & Rujukan per Kuartal
        for q_name, cols in q_map.items():
            for i, cat in enumerate(all_cats):
                val = pd.to_numeric(row.iloc[cols[i]], errors='coerce')
                item[f"{q_name}_{cat}"] = 1 if val == 1 else 0
        
        processed_data.append(item)
    
    res_df = pd.DataFrame(processed_data)
    
    # Tambah Kelompok Usia (per 5 tahun)
    bins = [0, 5, 10, 15, 20, 25, 100]
    labels = ['0-5 th', '6-10 th', '11-15 th', '16-20 th', '21-25 th', '26+ th']
    res_df['Kelompok Usia'] = pd.cut(res_df['Usia'], bins=bins, labels=labels)
    
    return res_df

# --- ANTARMUKA ---
st.title("🚀 MEL Monitoring Dashboard - Project BEN")

uploaded_file = st.file_uploader("Upload File Annex 14", type=["xlsx"])

if uploaded_file:
    df = load_and_process(uploaded_file)
    
    # Sidebar Filter
    st.sidebar.header("Filter Tampilan")
    mode = st.sidebar.radio("Lihat Data:", ["Kumulatif Tahunan", "Per Kuartal"])
    
    if mode == "Per Kuartal":
        q_pick = st.sidebar.selectbox("Pilih Kuartal:", ["Kuartal 1", "Kuartal 2", "Kuartal 3", "Kuartal 4"])
        # Filter kolom intervensi aktif
        inter_cols = [f"{q_pick}_{c}" for c in ['Kesehatan', 'Pendidikan', 'Mata Pencaharian', 'Sosial', 'Pemberdayaan']]
        ref_in = f"{q_pick}_Rujukan Dalam"
        ref_out = f"{q_pick}_Rujukan Luar"
    else:
        # Kumulatif: Jika pernah 1 di kuartal manapun
        for cat in ['Kesehatan', 'Pendidikan', 'Mata Pencaharian', 'Sosial', 'Pemberdayaan', 'Rujukan Dalam', 'Rujukan Luar']:
            df[cat] = df[[f"Kuartal {i}_{cat}" for i in range(1, 5)]].max(axis=1)
        inter_cols = ['Kesehatan', 'Pendidikan', 'Mata Pencaharian', 'Sosial', 'Pemberdayaan']
        ref_in, ref_out = 'Rujukan Dalam', 'Rujukan Luar'
        q_pick = "Tahunan"

    # --- VISUALISASI ---
    
    # Row 1: Intervensi & Kelompok Usia
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"1. Intervensi per Usia ({q_pick})")
        # Melelehkan dataframe untuk grafik batang bertumpuk
        melted_inter = df.melt(id_vars=['Kelompok Usia'], value_vars=inter_cols, var_name='Jenis', value_name='Total')
        fig1 = px.bar(melted_inter.groupby(['Kelompok Usia', 'Jenis']).sum().reset_index(), 
                      x='Kelompok Usia', y='Total', color='Jenis', barmode='group')
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.subheader("2. Total per Usia & Gender")
        fig2 = px.histogram(df, x='Kelompok Usia', color='Gender', barmode='group', text_auto=True)
        st.plotly_chart(fig2, use_container_width=True)

    # Row 2: Disabilitas Ganda & Ragam
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("3. Disabilitas Ganda (Usia & Gender)")
        df_ganda = df[df['Is_Ganda'] == 1]
        fig3 = px.bar(df_ganda.groupby(['Kelompok Usia', 'Gender']).size().reset_index(name='Jumlah'),
                      x='Kelompok Usia', y='Jumlah', color='Gender', barmode='group')
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        st.subheader("4. Ragam Disabilitas & Gender")
        fig4 = px.bar(df.groupby(['Ragam', 'Gender']).size().reset_index(name='Total'),
                      x='Total', y='Ragam', color='Gender', orientation='h')
        st.plotly_chart(fig4, use_container_width=True)

    # Row 3: Diagnosa Spesifik & Rujukan
    st.divider()
    c5, c6, c7 = st.columns(3)
    
    with c5:
        st.subheader("5. Kondisi Spesifik")
        spec_sum = df[['CP', 'Albinism', 'Down Syndrome', 'Kusta']].sum().reset_index()
        spec_sum.columns = ['Kondisi', 'Jumlah']
        st.dataframe(spec_sum, hide_index=True)
        st.bar_chart(spec_sum.set_index('Kondisi'))

    with c6:
        st.metric("6. Rujukan Dalam Kecamatan", int(df[ref_in].sum()))
        st.write("Target: Internal Organisasi")

    with c7:
        st.metric("7. Rujukan Luar Kecamatan", int(df[ref_out].sum()))
        st.write("Target: Eksternal Organisasi")

    st.subheader("Daftar Data Terproses")
    st.write(df[['Nama', 'Gender', 'Usia', 'Kelompok Usia', 'Ragam', 'Diagnosa'] + inter_cols])

else:
    st.warning("Silakan unggah file Excel Annex 14 untuk memulai analisis.")
