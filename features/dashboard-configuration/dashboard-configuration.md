# Abode Home Assistant Configuration

We need a new dashboard on the sidebard to configure the Abode alarm system. It will have 2 tabs for now:

- Modes:
    - Shows the 3 modes we have and which one is active: stand by, home, away. Under each group it shows the list of actions that apply to them
    - We might add an option to enable/disable the modes by time, location, etc.

- Actions:
    - A list of all the configured actions with their names, modes, enabled/disabled, and option to edit or delete
    - A button to add a new action

## Adding a new action

- Go to Abode dashboard on the sidebar
- Actions lists the name of all the configured actions with their names, modes, enabled/disabled, and option to edit or delete
- There's also an option to create a new action
- Clicking on new action opens a form
    - Title: The name of the new action
    - Modes: The 3 modes with a checkbox next to them. At least one of them needs to be picked
    - Sensors: The list of all the sensors grouped by categories with checkboxes and an option to select all that category. By default we display contact sensors (Window, Door, etc.), Motion, leaks, smoke, etc. (the regular ones for alarms), with an option to show others
    - Alarm(s) to trigger: Abode exposes several alarm switches, we display all the available ones with a checkbox next to them
    - Save: Saves the configuration and enables it 
