import cadquery as cq

# Define dimensions
body_length = 120  # mm
body_width = 70    # mm
body_thickness = 2  # mm
tab_width = 15      # mm
tab_length = 30     # mm
tab_thickness = 3   # mm
num_tabs = 20       # Number of tabs

# Create the main body
body = (
    cq.Workplane("XY")
    .box(body_length, body_width, body_thickness)
)

# Create tabs
for i in range(num_tabs):
    tab_position = (body_length / 2) - (tab_width / 2)
    tab_offset = (i - (num_tabs / 2)) * (tab_width + 5)  # 5 mm spacing
    tab = (
        cq.Workplane("XY")
        .translate((tab_position, tab_offset, body_thickness))
        .box(tab_width, tab_length, tab_thickness)
    )
    body = body.union(tab)

# Create a hole for hanging
hole = (
    cq.Workplane("XY")
    .center(0, body_width / 2 - 10)  # 10 mm from the top
    .circle(5)  # 5 mm diameter
    .cutThruAll()
)

# Combine body and hole
final_body = body.union(hole)

# Export to STEP file
cq.exporters.export(final_body, "shopping_list_organizer.step")

# Optionally export to STL for 3D printing
cq.exporters.export(final_body, "shopping_list_organizer.stl")
