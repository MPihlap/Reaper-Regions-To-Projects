import reapy
from reapy import reascript_api as RPR
import os
import time
import logging

def remove_items_in_region_except_bus(project, bus_track, pos, rgn_end):
    """
    For all tracks other than bus_track, remove or split item parts that lie within [pos, rgn_end].
    Splitting ensures only the portion inside the region is removed.
    """
    for track in project.tracks:
        if track == bus_track:
            continue

        # Iterate items in reverse order to safely modify while iterating
        for item in reversed(track.items):
            item_start = item.position
            item_end = item_start + item.length

            # Check if item overlaps the region
            if item_end <= pos or item_start >= rgn_end:
                # No overlap
                continue

            # Get raw pointers for ReaScript API
            track_ptr = track.id
            item_ptr = item.id

            # 1. Item completely inside the region
            if item_start >= pos and item_end <= rgn_end:
                RPR.DeleteTrackMediaItem(track_ptr, item_ptr)

            # 2. Item overlaps on the left side of the region
            elif item_start < pos < item_end <= rgn_end:
                # Split at pos
                right_item = RPR.SplitMediaItem(item_ptr, pos)
                if right_item:
                    # right_item is inside region, delete it
                    RPR.DeleteTrackMediaItem(track_ptr, right_item)
                else:
                    # If split fails, remove entire item
                    RPR.DeleteTrackMediaItem(track_ptr, item_ptr)

            # 3. Item overlaps on the right side of the region
            elif pos <= item_start < rgn_end < item_end:
                # Split at rgn_end
                right_item = RPR.SplitMediaItem(item_ptr, rgn_end)
                if right_item:
                    # Original item now ends at rgn_end (inside region), delete it
                    RPR.DeleteTrackMediaItem(track_ptr, item_ptr)
                    # right_item remains for the part after rgn_end
                else:
                    # If split fails, remove entire item
                    RPR.DeleteTrackMediaItem(track_ptr, item_ptr)

            # 4. Item crosses both boundaries
            else:
                # item_start < pos < rgn_end < item_end
                # Split at pos
                right_item = RPR.SplitMediaItem(item_ptr, pos)
                if not right_item:
                    # If first split fails, remove entire item
                    RPR.DeleteTrackMediaItem(track_ptr, item_ptr)
                    continue

                # Now right_item covers pos->item_end
                # Split right_item at rgn_end
                after_item = RPR.SplitMediaItem(right_item, rgn_end)
                # right_item now covers pos->rgn_end (inside region), after_item covers rgn_end->item_end
                # Delete the inside portion (right_item)
                RPR.DeleteTrackMediaItem(track_ptr, right_item)


def create_projects_from_regions():
    # Connect to the current REAPER project
    reapy.connect()
    project = reapy.Project()
    original_project_id = project.id
    project_name = project.name.split(".")[0]

    # Get total number of markers and regions
    retvals = RPR.CountProjectMarkers(project.id, 0, 0)
    num_markers = retvals[2]
    num_regions = retvals[3]
    num_markers_regions = num_markers + num_regions

    bus_created = False
    bus_track = None
    for i in range(num_markers_regions):
        retval, proj, idx, is_region, pos, rgn_end, name, markrgnindex, colorOut = RPR.EnumProjectMarkers3(
            project.id, i, 0, 0, 0, 0, 0, 0)
        logging.debug((retval, proj, idx, is_region, pos, rgn_end, name, markrgnindex, colorOut))

        if is_region:
            # Get region name via SWS
            fs = RPR.SNM_CreateFastString("")
            _ = RPR.SNM_GetProjectMarkerName(proj, markrgnindex, is_region, fs)
            region_name = RPR.SNM_GetFastString(fs)
            RPR.SNM_DeleteFastString(fs)

            if region_name.strip() == "":
                region_name = f"{markrgnindex}_{project_name}"
            else:
                region_name = f"{markrgnindex}_{region_name}_{project_name}"

            logging.debug(region_name)

            # Determine correct project path
            project_path = project.path
            while not os.path.exists(f"{project_path}/{project.name}"):
                project_path = os.path.dirname(project_path)
                logging.debug(project_path)

            subproject_path = f"{project_path}/{region_name}.rpp"
            logging.debug(subproject_path)

            # Save current project as the subproject
            RPR.Main_SaveProjectEx(project.id, subproject_path, 0)

            # Create a new project tab and open the subproject
            RPR.Main_OnCommand(40859, 0)  # New project tab
            RPR.Main_openProject(f"noprompt:{subproject_path}")

            subproject = reapy.Project()
            subproject.time_selection = (pos, rgn_end)

            while not subproject.has_valid_id:
                time.sleep(0.1)

            # Crop to time selection and save
            RPR.Main_OnCommand(40049, 0)
            RPR.SetEditCurPos(0, True, False)
            subproject.save()

            # Return to original project
            RPR.SelectProjectInstance(original_project_id)
            project = reapy.Project(original_project_id)
            # Create the "Subproject Bus" track if it doesn't exist
            if not bus_created:
                bus_track = project.add_track(name="Subproject Bus")
                bus_created = True

            # Insert the subproject onto the Subproject Bus track
            bus_track.select()
            project.cursor_position = pos
            items_before = len(bus_track.items)
            RPR.InsertMedia(subproject_path, 0)
            items_after = len(bus_track.items)
            if items_after > items_before:
                new_item = bus_track.items[-1]
                new_item.length = rgn_end - pos

            # Remove items overlapping this region from other tracks
            remove_items_in_region_except_bus(project, bus_track, pos, rgn_end)

            # Remove the exit() if you want to process all regions
            #exit()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    create_projects_from_regions()
