import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# Load the dataset
file_path = 'TimeSeriesData_DDoS.csv'
data = pd.read_csv(file_path)

# Convert 'Time' to minutes since the start
data['Timestamp'] = pd.to_datetime(data['Time'], format='%H:%M:%S')
start_time = data['Timestamp'].min()
data['TimeInMinutes'] = (data['Timestamp'] - start_time).dt.total_seconds() / 60

# Sort the data by time
data = data.sort_values('TimeInMinutes')

# Set global font properties
plt.rc('font', size=28, weight='bold')
font = FontProperties()
font.set_size(28)
font.set_weight('bold')

# Create subplots
fig, axes = plt.subplots(2, 3, figsize=(20, 10), dpi=100, constrained_layout=True)
(ax1, ax2, ax3), (ax4, ax5, ax6) = axes
# Function to set spine thickness
def set_spine_thickness(ax, linewidth):
    for spine in ax.spines.values():
        spine.set_linewidth(linewidth)

# Specify the desired spine linewidth
spine_linewidth = 3  # Adjust this value as needed

# Set spine thickness for each subplot
set_spine_thickness(ax1, spine_linewidth)
set_spine_thickness(ax2, spine_linewidth)
set_spine_thickness(ax3, spine_linewidth)
set_spine_thickness(ax4, spine_linewidth)
set_spine_thickness(ax5, spine_linewidth)
set_spine_thickness(ax6, spine_linewidth)
# Plotting

# Plot 1 - Attack Type
ax1.step(data['TimeInMinutes'], data['attack_type'], where='post', color='blue', linewidth=4)
ax1.set_xlabel('time (m)', fontproperties=font)
ax1.set_ylabel('external\nuser type', fontproperties=font)
ax1.set_xlim(0, 30)
ax1.set_xticks(range(0, 31, 10))

# Plot 2 - Protocol
ax2.step(data['TimeInMinutes'], data['Protocol'], where='post', color='blue', linewidth=4)
ax2.set_xlabel('time (m)', fontproperties=font)
ax2.set_ylabel('protocol', fontproperties=font)
ax2.set_xlim(0, 30)
ax2.set_xticks(range(0, 31, 10))

# Plot 3 - Port
ax3.step(data['TimeInMinutes'], data['Port'], where='post', color='blue', linewidth=4)
ax3.set_xlabel('time (m)', fontproperties=font)
ax3.set_ylabel('port', fontproperties=font)
ax3.set_xlim(0, 30)
ax3.set_xticks(range(0, 31, 10))

# Plot 4 - Packet Size
ax4.plot(data['TimeInMinutes'], data['packet_size'], color='blue', linewidth=4)
ax4.set_xlabel('time (m)', fontproperties=font)
ax4.set_ylabel('packet size', fontproperties=font)
ax4.set_xlim(0, 30)
ax4.set_xticks(range(0, 31, 10))

# Plot 5 - Flow Total
ax5.plot(data['TimeInMinutes'], data['Flow Total'], color='blue', linewidth=4)
ax5.set_xlabel('time (m)', fontproperties=font)
ax5.set_ylabel('num_flows', fontproperties=font)
ax5.set_xlim(0, 30)
ax5.set_xticks(range(0, 31, 10))

# Plot 6 - Unreplied
ax6.plot(data['TimeInMinutes'], data['Unreplied'], color='blue', linewidth=4)
ax6.set_xlabel('time (m)', fontproperties=font)
ax6.set_ylabel('num_unreplied', fontproperties=font)
ax6.set_xlim(0, 30)
ax6.set_xticks(range(0, 31, 10))

# Layout adjustments
plt.tight_layout()
plt.subplots_adjust(wspace=0.6, hspace=0.4)

# Save the figure in PDF format
filename_separate = 'Fig/6-plot.pdf'
plt.savefig(filename_separate, format='pdf', bbox_inches='tight')
plt.show()


#
# Flow Total
# packet_size
# attack_type