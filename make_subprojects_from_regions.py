import reapy
from reapy import reascript_api as RPR
import os
#from sws_python import *

def create_subprojects_from_regions():
    # Ensure REAPER is running and accessible
    #reapy.config.reaper_python_library = 'C:/path/to/your/reaper_python.dll'  # Update this path accordingly

    # Connect to the current REAPER project
    reapy.connect()
    project = reapy.Project()
    original_project_id = project.id
    project_name = project.name.split(".")[0]

    # Get the total number of markers and regions
    num_markers_regions = RPR.CountProjectMarkers(project.id, 0, 0)
    num_markers_regions = num_markers_regions[-1] + num_markers_regions[-2]
    #num_regions = RPR.CountProjectMarkers(project.id, 0, 1)[-1]

    #print(num_markers, num_regions)
    
    # Loop through all markers and regions
    for i in range(num_markers_regions):
        #ret, is_region, pos, rgn_end, name, markrgnindex, color = RPR.EnumProjectMarkers3(project.id, i, 0, 0, 0, 0, 0, 0)
        retval, proj, idx, is_region, pos, rgn_end, name, markrgnindex, colorOut = RPR.EnumProjectMarkers3(project.id, i, 0, 0, 0, 0, 0, 0)
        #print(project.markers)
        #print(retval, proj, idx, is_region, pos, rgn_end, name, markrgnindex, colorOut)
        
        fs = RPR.SNM_CreateFastString("")
        name = RPR.SNM_GetProjectMarkerName(proj, idx, is_region, fs)
        print(name)
        name = RPR.SNM_GetFastString(fs)
        #print(fs)
        print(name)
        if is_region:
            # Enum name is always 0, workaround needed.
            region_name = f"{markrgnindex}_{name}_{project_name}" if name else f"{markrgnindex}_{project_name}"
            RPR.SNM_DeleteFastString(fs)
            #reapy.print(region_name)
            #continue
            # Set the time selection to the region
            project.time_selection = (pos, rgn_end)
            
            # Copy items in the time selection to a new project
            project.select_all_items()
            # Select all tracks in the project
            RPR.Main_OnCommand(40296, 0)  # Select all tracks

            RPR.Main_OnCommand(40060, 0)  # Copy items
            
            # Create a new project tab for the subproject
            RPR.Main_OnCommand(40859, 0)  # New project tab
            
            # Get the new project
            subproject = reapy.Project()
            
            # Paste items in the new project tab
            RPR.Main_OnCommand(40058, 0)  # Paste items
            
            # Save the subproject
            subproject_path = f"{project.path}/{region_name}.rpp"
            print(subproject_path)
            RPR.Main_SaveProjectEx(subproject.id, subproject_path, 0)
            RPR.Main_openProject(f"noprompt:{subproject_path}")
            #subproject.save(f"{region_name}.rpp")
            
            # Close the subproject tab
            #RPR.Main_OnCommand(40861, 0)  # Close project tab
            # Switch back to the original project using its ID
            RPR.SelectProjectInstance(original_project_id)
        

    # Disconnect from REAPER
    #reapy.disconnect()

# Run the function
create_subprojects_from_regions()
