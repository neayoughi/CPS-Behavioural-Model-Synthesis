
import matplotlib.pyplot as plt
import numpy as np


plt.rcParams.update({
    'font.size': 32,
    'font.weight': 'bold',
    'axes.labelweight': 'bold',
    'axes.titleweight': 'bold',
    'xtick.labelsize': 22,
    'ytick.labelsize': 24
})

meanprops = {
    # 'marker': '-',          # Use a circle as the marker
    'linestyle': 'dashed',
    'linewidth': 5,
    'color': 'black'
    # 'markerfacecolor': 'black',  # Black fill
    # 'markeredgecolor': 'black',  # Black edge color
    # 'markersize': 10,       # Size of the marker
    # 'markeredgewidth': 10,  # Edge width of the marker
    # 'markeredgecolor': 'black'   # Edge color of the marker
}

# Data from the tables in the image
data_1st = {
    "DoS3": [100] * 10,
    "DoS3_Naive": [100, 70, 50, 28, 28, 86, 40, 22, 22, 8],
    "DoS5": [100] * 10,
    "DoS5_Naive": [100, 100, 100, 84, 52, 100, 100, 100, 70, 66],
    "DDoS3": [100] * 10,
    "DDoS3_Naive": [100, 74, 48, 46, 32, 100, 100, 100, 100, 88]
}

data_2nd = {
    "DoS3": [100] * 10,
    "DoS3_Naive": [100, 88, 46, 42, 22, 100, 86, 64, 46, 28],
    "DoS5": [100, 88, 50, 38, 40, 100, 66, 38, 34, 24],
    "DoS5_Naive": [100, 80, 57.99, 40, 28, 100, 68, 42, 22, 24],
    "DDoS3": [100] * 10,
    "DDoS3_Naive": [100] * 10
}

data_top2 = {
    "DoS3": [100, 72, 56, 36, 30, 100, 46, 20, 28, 18],
    "DoS3_Naive": [100, 76, 60, 38, 28, 78, 34, 24, 10, 6],
    "DoS5": [100] * 10,
    "DoS5_Naive": [38, 26, 18, 8, 6, 24, 14, 16, 2, 4],
    "DDoS3": [100] * 10,
    # "DDOS3_Naive": [44, 18, 18, 8, 10, 100, 100, 68, 44, 40],
    "DDoS3_Naive": [44, 26, 22, 12, 12, 100, 100, 100, 90, 82]
}

# Algorithm and Naive data separated for each metric
alg_data = {
    '1st': {'DoS3': data_1st['DoS3'], 'DoS5': data_1st['DoS5'], 'DDoS3': data_1st['DDoS3']},
    '2nd': {'DoS3': data_2nd['DoS3'], 'DoS5': data_2nd['DoS5'], 'DDoS3': data_2nd['DDoS3']},
    'Top-2': {'DoS3': data_top2['DoS3'], 'DoS5': data_top2['DoS5'], 'DDoS3': data_top2['DDoS3']}
}

naive_data = {
    '1st': {'DoS3': data_1st['DoS3_Naive'], 'DoS5': data_1st['DoS5_Naive'], 'DDoS3': data_1st['DDoS3_Naive']},
    '2nd': {'DoS3': data_2nd['DoS3_Naive'], 'DoS5': data_2nd['DoS5_Naive'], 'DDoS3': data_2nd['DDoS3_Naive']},
    'Top-2': {'DoS3': data_top2['DoS3_Naive'], 'DoS5': data_top2['DoS5_Naive'], 'DDoS3': data_top2['DDoS3_Naive']}
}

# Function to plot individual pair of boxplots for Algorithm vs Naive
def plot_paired_boxplots(ax, alg_data, naive_data, title):
    data = [alg_data, naive_data]
    # bp = ax.boxplot(data, positions=[1, 2], showmeans=True)
    bp = ax.boxplot(data, meanprops=meanprops, meanline=True, showmeans=True)
# Increase the linewidth of the boxplot elements
    linewidth = 2  # Set this to your desired linewidth
    for element in ['boxes', 'whiskers', 'caps', 'medians']:
        plt.setp(bp[element], linewidth=linewidth)

    # Iterate over the plotted lines and boxes to get the mean values
    means = [item.get_ydata()[0] for item in bp['means']]

    # Annotate the mean values on the plot
    for i, mean in enumerate(means):
        # ax.text(i + 1, mean, f'{mean:.2f}', ha='center', va='bottom', fontsize=18, color='black', weight='bold', bbox=dict(facecolor='gray',alpha=0.7, edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(i + 1, mean, f'{mean:.2f}', ha='center', va='bottom', fontsize=22, color='black', weight='bold',
                bbox=dict(facecolor='gray', alpha=0.4, edgecolor='none', boxstyle='round,pad=0.5'))

    ax.set_xticks([1, 2])
    # ax.set_xticklabels(['MELA', 'Manual'])
    ax.set_xticklabels(['\n'.join(["MELA"]), '\n'.join(["BASELINE"])],
                       fontdict={'fontvariant': 'small-caps'})  # Small caps for MELA and BASELINE
    # ax.set_title(title)

    # Set mean line properties
    mean_line_width = 5  # Adjust this for line thickness
    mean_line_color = 'blue'  # Color of the mean line
    mean_line_style = 'solid'  # Line style, e.g., 'solid', 'dashed', etc.

    for mean_line in bp['means']:
        mean_line.set_color(mean_line_color)
        mean_line.set_linewidth(mean_line_width)
        mean_line.set_linestyle(mean_line_style)
        mean_line.set_zorder(5)  # Ensure the mean line is above other plot elements



# Inverting the layout of the plots
fig, axes = plt.subplots(3, 3, figsize=(15, 15), constrained_layout=True)

# Adjust spacing at the top of the figure to make room for the titles
# fig.subplots_adjust(top=0.88)  # Adjust the value as needed

for ax in axes.flat:
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom - (top-bottom)*0.3, top)

for ax in axes.flat:
    for label in ax.get_yticklabels():
        label.set_weight('bold')

for ax in axes.flat:
    for label in ax.get_xticklabels():
        label.set_weight('bold')

for ax in axes.flat:
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)


# If you need to add more space between the subplots themselves, adjust 'hspace'
plt.subplots_adjust(hspace=20)  # Adjust the value as needed for vertical spacing


# Row and column titles
col_titles = ['1st', '2nd', 'Top-2']
col_display_titles = {
    '1st': 'num_flows',
    '2nd': 'num_unreplied',
    'Top-2': 'flow_unreplied'
}
# row_titles = ['DoS3', 'DDoS3', 'DOS5']
row_titles = ['DoS3', 'DDoS3', 'DoS5']
# Plotting the boxplots with inverted layout
for j, metric in enumerate(col_titles):
    for i, alg in enumerate(row_titles):
        plot_paired_boxplots(
            axes[i, j],
            alg_data[metric][row_titles[i]],
            naive_data[metric][row_titles[i]],
            f'{alg} - {metric}'
        )


# Setting the column titles with metrics
for ax, col_title in zip(axes[0], col_titles):
    # ax.set_title(col_title)
    # ax.set_title(col_title, pad=20)
    ax.set_title(col_display_titles[col_title], fontfamily='monospace', fontsize=28, fontweight='bold', pad=20)  # Bigger, bold monospaced variable names


# Setting the row titles with algorithms
for ax, row_title in zip(axes[:,0], row_titles):
    ax.set_ylabel(row_title, rotation=90, size='large', labelpad=15)
    # ax.yaxis.set_label_coords(-0.3, 0.5)
    ax.yaxis.label.set_position((ax.yaxis.label.get_position()[0], ax.yaxis.label.get_position()[1] + 0.2))



# Loop over all axes and set the y-axis limit
for row in axes:
    for ax in row:
        ax.set_ylim(bottom=0, top=110)  # Set the limits from 0 to 100



# Adjust these values as needed for proper alignment
x_position = -0.15  # Adjust this value to move the label left or right
y_offset = 0.5      # Adjust this value to move the label up or down

for ax, row_title in zip(axes[:,0], row_titles):
    ax.set_ylabel(row_title + '\nAccuracy(%)', rotation=90, fontsize=32, fontweight='bold', labelpad=20)
    ax.yaxis.label.set_position((x_position, y_offset))


fig.savefig('/mnt/data/boxplot_2_updated_bold.pdf', dpi=300, bbox_inches='tight')
fig.savefig('/mnt/data/boxplot_2_updated_bold.png', dpi=300, bbox_inches='tight')
plt.show()
