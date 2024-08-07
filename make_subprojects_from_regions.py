import reapy
from reapy import reascript_api as RPR
import os
import time
import logging

def create_projects_from_regions():

    # Connect to the current REAPER project
    reapy.connect()
    project = reapy.Project()
    original_project_id = project.id
    project_name = project.name.split(".")[0]

    # Get the total number of markers and regions
    num_markers_regions = RPR.CountProjectMarkers(project.id, 0, 0)
    num_markers_regions = num_markers_regions[-1] + num_markers_regions[-2]
    
    # Loop through all markers and regions
    for i in range(num_markers_regions):
        #ret, is_region, pos, rgn_end, name, markrgnindex, color = RPR.EnumProjectMarkers3(project.id, i, 0, 0, 0, 0, 0, 0)
        retval, proj, idx, is_region, pos, rgn_end, name, markrgnindex, colorOut = RPR.EnumProjectMarkers3(project.id, i, 0, 0, 0, 0, 0, 0)
        logging.debug(retval, proj, idx, is_region, pos, rgn_end, name, markrgnindex, colorOut)
        
        if is_region:
            # EnumProjectMarkers3 fails to return name, SWS workaround needed.
            fs = RPR.SNM_CreateFastString("")
            name = RPR.SNM_GetProjectMarkerName(proj, markrgnindex, is_region, fs)
            name = RPR.SNM_GetFastString(fs)
            RPR.SNM_DeleteFastString(fs)
            # Enum name is always 0, workaround needed.
            region_name = f"{markrgnindex}_{name}_{project_name}" if name else f"{markrgnindex}_{project_name}"
            logging.debug(region_name)
            # Save the subproject
            logging.debug(project.path)
            project_path = project.path
            # For some reason reapy reports the media folder (if setup) as the project path. Recurse back to the project folder.
            while not os.path.exists(f"{project_path}/{project.name}"):
                project_path = os.path.dirname(project.path)
                logging.debug(project_path)
            subproject_path = f"{project_path}/{region_name}.rpp"
            logging.debug(subproject_path)
            RPR.Main_SaveProjectEx(project.id, subproject_path, 0)
            # Create a new project tab for the subproject
            RPR.Main_OnCommand(40859, 0)  # New project tab
            RPR.Main_openProject(f"noprompt:{subproject_path}")
            # Get the new project
            subproject = reapy.Project()
            # Set the time selection to the region
            subproject.time_selection = (pos, rgn_end)
            # Wait until the project is fully loaded
            while not project.has_valid_id:
                time.sleep(0.1)  # Wait 100 ms and check again
            RPR.Main_OnCommand(40049, 0)  # Crop to time selection
            RPR.SetEditCurPos(0, True, False) # Set cursor to start of project
            subproject.save()
            
            RPR.SelectProjectInstance(original_project_id)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_projects_from_regions()
