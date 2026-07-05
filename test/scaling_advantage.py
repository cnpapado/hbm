# import matplotlib.pyplot as plt
# import numpy as np
# from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
# import matplotlib.patches as patches

# # ================== HPCA/ISCA PUBLICATION STYLE ==================
# plt.rcParams.update({
#     "font.family": "serif",
#     "font.size": 50,
#     "axes.titlesize": 45,
#     "axes.labelsize": 45,
#     "axes.labelweight": "bold",
#     "axes.titleweight": "bold",
#     "axes.linewidth": 4.0,     # Bolder boxes
#     "xtick.labelsize": 48,
#     "ytick.labelsize": 48,
#     "xtick.major.size": 15,
#     "xtick.major.width": 4,
#     "ytick.major.size": 15,
#     "ytick.major.width": 4,
#     "figure.figsize": (25, 18),
#     "savefig.dpi": 300,
#     "pdf.fonttype": 42,
#     "ps.fonttype": 42,
#     "text.usetex": False
# })

# # 1. Generate Scaling Data
# N = np.linspace(1, 256, 1000)
# y_2d = 4 * np.sqrt(N)
# y_3d = N

# # 2. Main Plotting
# fig, ax = plt.subplots()

# # Plot 3D Scaling (Linear)
# ax.plot(N, y_3d, label='HBMS Architecture ($O(N)$)', 
#          color='#1f77b4', linewidth=10, linestyle='-')

# # Plot 2D Scaling (Sub-linear)
# ax.plot(N, y_2d, label='2D Planar ($O(4\sqrt{N})$)', 
#          color='#d62728', linewidth=10, linestyle='--')

# # 3. Shading and Branding the HBMS Advantage
# # Update the legend label and fill the area
# ax.fill_between(N, y_2d, y_3d, where=(y_3d >= y_2d), 
#                 color='#1f77b4', alpha=0.2, label='HBMS Advantage Area')

# # Adding a stylized text label directly into the shaded region
# # We'll place it at N=165, Y=110 to sit comfortably in the center-right gap
# # ax.text(165, 110, "HBMS ADVANTAGE AREA", 
# #         fontsize=44, 
# #         color='#1f77b4', 
# #         fontweight='black',  # Use 'black' for maximum weight
# #         rotation=38,         # Aligns with the slope of the O(N) line
# #         ha='center', 
# #         va='center',
# #         alpha=0.85)

# # 3.5. Adding text label to the shaded advantage area
# # Coordinates (160, 100) place it in the center-right of the blue zone
# ax.text(180, 100, "HBMS Advantage Area", 
#         fontsize=42, 
#         color='#1f77b4', 
#         fontweight='bold', 
#         rotation=0,      # Rotates text to match the slope of the 3D scaling
#         ha='center', 
#         va='center',
#         alpha=0.9)

# # 4. Main Plot Formatting
# # Increased fontsize to 55 for title and 50 for labels
# # ax.set_title("3D vs. 2D Scaling Advantage", pad=40, fontsize=55)
# ax.set_xlabel("Number of Data Qubits ($N$)", labelpad=28, fontsize=50)
# ax.set_ylabel("Magic State Delivery ($M$)", labelpad=28, fontsize=50)

# ax.grid(True, linestyle='--', alpha=0.5, linewidth=2)

# # Move Legend to lower right to make space for inset in upper left
# ax.legend(loc='lower right', fontsize=32, frameon=True, edgecolor='black')

# ax.set_xticks([]) # Removes x-axis ticks and labels
# ax.set_yticks([]) # Removes y-axis ticks and labels

# ax.set_xlim(0, 260)
# ax.set_ylim(0, 260)

# # 5. Inset Subfigure - Moved to UPPER LEFT
# # loc=2 is upper left
# # Reduced size (35% width, 35% height) to allow more main plot visibility
# ax_inset = inset_axes(ax, width="35%", height="35%", loc='upper left', borderpad=5)

# # Plot same lines in inset
# ax_inset.plot(N, y_3d, color='#1f77b4', linewidth=8, linestyle='-')
# ax_inset.plot(N, y_2d, color='#d62728', linewidth=8, linestyle='--')
# ax_inset.fill_between(N, y_2d, y_3d, where=(y_3d >= y_2d), color='#1f77b4', alpha=0.2)
# ax_inset.fill_between(N, y_2d, y_3d, where=(y_2d > y_3d), color='#d62728', alpha=0.1)

# # 6. Inset Axis Formatting - Tighter Zoom at N=16
# ax_inset.set_xlim(8, 24)
# ax_inset.set_ylim(8, 24)
# ax_inset.set_xticks([ 16 ])
# ax_inset.set_yticks([ 16 ])
# ax_inset.tick_params(labelsize=32, width=3, length=10)
# for spine in ax_inset.spines.values():
#     spine.set_linewidth(3)

# # 7. Add Highlight Circle at Crossover Point (16, 16)
# # Transparent yellow circle for emphasis
# crossover_highlight = patches.Circle((16, 16), 2.0, color='yellow', alpha=0.4, zorder=5)
# ax_inset.add_patch(crossover_highlight)
# # Black marker for precision
# ax_inset.plot(16, 16, 'ko', markersize=14, zorder=11)

# ax_inset.annotate('Crossover (N=16)', xy=(16, 16), xytext=(9, 21), 
#                   fontsize=32, fontweight='bold', arrowprops=dict(facecolor='black', shrink=0.05, width=2))

# # Connectors from main plot to zoom
# mark_inset(ax, ax_inset, loc1=3, loc2=4, fc="none", ec="0.5", lw=2, linestyle=':')

# plt.tight_layout()
# # plt.savefig('scaling_advantage_final_v3.png')
# plt.savefig('plots_new/scaling_advantage_final_v4.pdf')

# print("[✓] Scaling advantage plot with reduced inset saved successfully.")

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
import matplotlib.patches as patches

# ================== YOUR CUSTOM STYLE (UNTOUCHED) ==================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 50,
    "axes.titlesize": 45,
    "axes.labelsize": 45,
    "axes.labelweight": "bold",
    "axes.titleweight": "bold",
    "axes.linewidth": 4.0,     # Bolder boxes
    "xtick.labelsize": 48,
    "ytick.labelsize": 48,
    "xtick.major.size": 15,
    "xtick.major.width": 4,
    "ytick.major.size": 15,
    "ytick.major.width": 4,
    "figure.figsize": (25, 18),
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "text.usetex": False
})

# 1. Generate Scaling Data
N = np.linspace(1, 256, 1000)
y_2d = 4 * np.sqrt(N)
y_3d = N

# 2. Main Plotting
fig, ax = plt.subplots()

# Improved Color Palette
color_3d = '#004c6d' # Deep Blue
color_2d = '#de425b' # Coral Red



# Plot 2D Scaling (Sub-linear)
ax.plot(N, y_2d, label='2D Planar ($O(4\sqrt{N})$)', 
         color=color_2d, linewidth=12, linestyle='--', solid_capstyle='round')

# Plot 3D Scaling (Linear)
ax.plot(N, y_3d, label='HBMS Architecture ($O(N)$)', 
         color=color_3d, linewidth=12, linestyle='-', solid_capstyle='round')

# 3. Shading and Branding the HBMS Advantage
ax.fill_between(N, y_2d, y_3d, where=(y_3d >= y_2d), 
                color=color_3d, alpha=0.15, label='HBMS Advantage Area')

# Stylized text label
ax.text(180, 100, "HBMS Advantage Area", 
        fontsize=42, 
        color=color_3d, 
        fontweight='bold', 
        ha='center', 
        va='center',
        alpha=0.8)

# 4. Main Plot Formatting
ax.set_xlabel("Number of Data Qubits ($N$)", labelpad=28)
ax.set_ylabel("Magic State Delivery ($M$)", labelpad=28)

# --- BEAUTY UPDATE: REMOVE TOP AND RIGHT BORDERS ---
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Light grid for better readability
ax.grid(True, linestyle=':', alpha=0.4, linewidth=3)

# Legend without the box frame
ax.legend(loc='lower right', fontsize=32, frameon=False)

# Keep the axes clean (removing specific ticks as in your original)
ax.set_xticks([]) 
ax.set_yticks([]) 

ax.set_xlim(0, 260)
ax.set_ylim(0, 260)

# 5. Inset Subfigure - Cleaned up to match
ax_inset = inset_axes(ax, width="35%", height="35%", loc='upper left', borderpad=5)

ax_inset.plot(N, y_3d, color=color_3d, linewidth=8, linestyle='-')
ax_inset.plot(N, y_2d, color=color_2d, linewidth=8, linestyle='--')
ax_inset.fill_between(N, y_2d, y_3d, where=(y_3d >= y_2d), color=color_3d, alpha=0.15)

# Despine the inset as well
ax_inset.spines['top'].set_visible(False)
ax_inset.spines['right'].set_visible(False)

# 6. Inset Axis Formatting
ax_inset.set_xlim(8, 24)
ax_inset.set_ylim(8, 24)
ax_inset.set_xticks([16])
ax_inset.set_yticks([16])
ax_inset.tick_params(labelsize=32, width=3, length=10)
for spine in ax_inset.spines.values():
    spine.set_linewidth(3)

# 7. Add Highlight Circle at Crossover Point
crossover_highlight = patches.Circle((16, 16), 1.5, color='#f9bc08', alpha=0.6, zorder=5)
ax_inset.add_patch(crossover_highlight)
ax_inset.plot(16, 16, 'ko', markersize=14, zorder=11)

ax_inset.annotate('Crossover (N=16)', xy=(16, 16), xytext=(9, 21), 
                  fontsize=32, fontweight='bold', 
                  arrowprops=dict(arrowstyle="->", color='black', lw=3))

# Connectors from main plot to zoom
mark_inset(ax, ax_inset, loc1=3, loc2=4, fc="none", ec="0.6", lw=3, linestyle='--')

plt.tight_layout()
plt.savefig('scaling_advantage_clean_bold.pdf', bbox_inches='tight')
plt.show()