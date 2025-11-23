# How to Enable Debug Logging for Abode Security

## Enable Logging in Home Assistant configuration.yaml

Add this to your `configuration.yaml` file:

```yaml
logger:
  logs:
    custom_components.abode_security: debug
    jaraco.abode: debug
    jaraco.abode.client: debug
    jaraco.abode.event_controller: debug
```

Then restart Home Assistant (or reload the configuration if supported).

## What You'll See

### When Integration Loads:

```
INFO (MainThread) [custom_components.abode_security.switch] Test mode switch added to Home Assistant, fetching initial status
DEBUG (MainThread) [custom_components.abode_security.models] get_test_mode() returned: False (type: <class 'bool'>)
INFO (MainThread) [custom_components.abode_security.switch] Initial test mode status fetched: False
DEBUG (MainThread) [custom_components.abode_security.switch] Enabling polling after initial sync
```

### API Level Debug Logs:

```
DEBUG (MainThread) [jaraco.abode.client] API Request - method=get, path=https://api.goabode.com/v1/cmsettings, data=None
DEBUG (MainThread) [jaraco.abode.client] API Response - status=200
DEBUG (MainThread) [jaraco.abode.client] Get Test Mode Response (raw): {"testModeActive": true, ...}
DEBUG (MainThread) [jaraco.abode.client] Get Test Mode Response (parsed): {'testModeActive': True, ...}
DEBUG (MainThread) [jaraco.abode.client] Response keys: ['testModeActive', ...]
DEBUG (MainThread) [jaraco.abode.client] testModeActive field value: True (from key: testModeActive)
INFO (MainThread) [jaraco.abode.client] Test mode is currently: enabled
```

## Key Things to Check

1. **API Status Code**: Should be 200 (success)
   - If not 200, there's a network/auth issue

2. **Response JSON**: Look for `testModeActive` field
   - If missing, the API schema has changed

3. **testModeActive Value**: Should match what you see on Abode's website
   - If doesn't match, check if you're querying the right endpoint

4. **get_test_mode() Returned Value**: Should match testModeActive
   - If doesn't match, there's a parsing issue

## Finding the Logs

### In Docker Container (ha-dev):

```bash
docker logs ha-dev-config -f | grep -i "abode\|test"
```

Or access logs through Home Assistant UI:
1. Settings → System → Logs
2. Search for "abode" or "test"

### In Configuration Files:

Home Assistant logs are typically in:
- `ha-dev-config/home-assistant.log`
- Or check the container output with `docker logs`

## If You See Errors

### Error: "testModeActive field missing from response"
- API response doesn't contain the field
- The API schema or endpoint may have changed
- Share the full response JSON from logs

### Error: "Expected True, got False" (or opposite)
- API returned wrong value
- Could be that test mode didn't actually toggle on Abode's side
- Check if there are permission issues

### Error: "API Request - status=401"
- Authentication failed
- Your Abode credentials may have changed
- Try re-adding the integration

## Next Steps

1. Add debug logging to `configuration.yaml`
2. Restart Home Assistant
3. Let the integration initialize
4. Check the logs for the messages above
5. **Share the logs** (especially API Request/Response sections)

This will give us the actual data being sent/received to diagnose the issue.
