import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import uuid
import os
import pandas as pd
import numpy as np

def generate_chart(df, title="Data Insights"):
    if df.empty:
        return None
    MAX_ROWS_FOR_CHART = 100
    if len(df) > MAX_ROWS_FOR_CHART:
        print(f"Warning: Chart data has been truncated to the first {MAX_ROWS_FOR_CHART} rows.")
        df = df.head(MAX_ROWS_FOR_CHART)

    charts_dir = os.path.join("static", "charts")
    os.makedirs(charts_dir, exist_ok=True)
    filename = f"chart_{uuid.uuid4().hex}.png"
    chart_path = os.path.join(charts_dir, filename)

    BG_COLOR, PRIMARY_BLUE, TEXT_DEEP_BLUE, TEXT_PRIMARY, GRID_COLOR = "#FFFFFF", "#e3f2fd", "#265f94", "#333333", "#E0E0E0"

    # --- DATE FIX START ---
    cols_lower = {c.lower(): c for c in df.columns}

    def _find(*names):
        for n in names:
            if n.lower() in cols_lower:
                return cols_lower[n.lower()]
        return None

    date_col = _find("From_Date", "From Date", "Date",)
    df_copy = df.copy()

    if date_col:
        df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
        first_col_name = date_col
    else:
        year_col = _find("From_Date", "Year")
        month_col = _find("From_Date", "From_Date", "Month")
        day_col = _find("From_Date", "Day")

        if year_col:
            years = pd.to_numeric(df_copy[year_col], errors="coerce")
            months = pd.Series(1, index=df_copy.index)
            days = pd.Series(1, index=df_copy.index)
            if month_col:
                months = pd.to_numeric(df_copy[month_col], errors="coerce").fillna(1)
            if day_col:
                days = pd.to_numeric(df_copy[day_col], errors="coerce").fillna(1)
            df_copy["Years"] = pd.to_datetime(
                {"year": years, "month": months, "day": days}, errors="coerce"
            )
            first_col_name = "Years"
        else:
            first_col_name = df.columns[0]
            df_copy[first_col_name] = pd.to_datetime(df_copy[first_col_name], errors='coerce')
    # --- DATE FIX END ---

    df_copy.dropna(subset=[first_col_name], inplace=True)
    
    is_date_axis = not df_copy.empty and pd.api.types.is_datetime64_any_dtype(df_copy[first_col_name])

    if df.shape == (1, 1):
        fig, ax = plt.subplots(figsize=(8, 5), facecolor=BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        kpi_name = df.columns[0]
        kpi_value = df.iloc[0, 0]
        plot_value = kpi_value if pd.notna(kpi_value) else 0
        display_label = f'{kpi_value:,.2f}' if pd.notna(kpi_value) else "N/A"
        
        bars = ax.bar([kpi_name], [plot_value], color=PRIMARY_BLUE, width=0.4)
        ax.set_ylabel("Value", color=TEXT_DEEP_BLUE)
        ax.annotate(display_label, xy=(bars[0].get_x() + bars[0].get_width() / 2, plot_value), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=12)

    elif is_date_axis:
        df = df_copy.sort_values(by=first_col_name)
        fig, ax = plt.subplots(figsize=(12, 6), facecolor=BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        
        if len(df.columns) > 2:
            category_col, value_col = df.columns[1], df.columns[2]
            pivoted_df = df.pivot_table(index=first_col_name, columns=category_col, values=value_col, aggfunc='sum')
            pivoted_df.plot(kind='line', ax=ax, marker='o', linestyle='-')
            ax.set_ylabel(value_col)
            ax.legend(title=category_col)
        else:
            ax.plot(df[first_col_name], df.iloc[:, 1], marker='o', linestyle='-')
            ax.set_ylabel(df.columns[1])
            
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()
        ax.set_xlabel(first_col_name)

    else:
        if len(df.columns) == 1:
            fig, ax = plt.subplots(figsize=(12, 6), facecolor=BG_COLOR)
            ax.set_facecolor(BG_COLOR)
            value_counts = df[first_col_name].value_counts()
            x_labels = [str(label)[:20] for label in value_counts.index]
            ax.bar(x_labels, value_counts.values, color=PRIMARY_BLUE)
            ax.set_ylabel("Count")
            ax.set_xlabel(first_col_name)
            plt.xticks(rotation=45, ha='right')

        else:
            x_labels = [str(label)[:20] for label in df[first_col_name].fillna("N/A")]
            numeric_cols = [col for col in df.columns[1:] if pd.api.types.is_numeric_dtype(df[col])]
            if not numeric_cols: return None

            num_plots = len(numeric_cols)
            fig, axs = plt.subplots(num_plots, 1, figsize=(12, 5 * num_plots), facecolor=BG_COLOR, squeeze=False)
            axs = axs.flatten()

            for i, col in enumerate(numeric_cols):
                ax = axs[i]
                ax.set_facecolor(BG_COLOR)
                bars = ax.bar(x_labels, df[col], color=PRIMARY_BLUE, width=0.8)
                ax.set_ylabel(col, color=TEXT_DEEP_BLUE)

                if len(df) <= 20:
                    for bar in bars:
                        height = bar.get_height()
                        if pd.notna(height):
                            ax.annotate(f'{height:,.2f}', xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
            
            axs[-1].set_xlabel(first_col_name, color=TEXT_DEEP_BLUE)
            plt.setp(axs[-1].get_xticklabels(), rotation=45, ha='right')
            for ax in axs[:-1]:
                plt.setp(ax.get_xticklabels(), visible=False)

    if 'axs' in locals() and len(axs) > 1:
        fig.suptitle(title, fontsize=18, weight='bold', color=TEXT_DEEP_BLUE)
    else:
        ax = fig.get_axes()[0]
        ax.set_title(title, fontsize=16, weight='bold', pad=20, color=TEXT_DEEP_BLUE)
    
    for ax in fig.get_axes():
        for spine in ax.spines.values(): spine.set_visible(False)
        ax.grid(True, axis='y', linestyle='--', linewidth=0.7, color=GRID_COLOR)
        ax.set_axisbelow(True)
        ax.tick_params(colors=TEXT_PRIMARY, length=0)
        plt.setp(ax.get_yticklabels(), color=TEXT_PRIMARY)
        if not any(tick.get_rotation() for tick in ax.get_xticklabels()):
            plt.setp(ax.get_xticklabels(), rotation=0)

    plt.tight_layout(rect=[0, 0, 1, 0.96] if 'axs' in locals() and len(axs) > 1 else None)
    plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)

    return filename
