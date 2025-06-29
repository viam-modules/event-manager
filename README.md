# event-manager modular service

*event-manager* is a Viam module that provides logic and eventing capabilities using the sensor component API through the viam:event-manager:eventing model.

The event manager can be used in conjunction with a mobile app or web app, which provides a user interface for configuring and managing events.

The event manager can be configured with rules to evaluate, based on:

* Time of day
* Computer vision detections
* Computer vision classifications
* Computer vision tracker events (new person seen that is not an approved person)
* Output from sensors and generic components/services

When a rule is triggers, configured notification actions can occur of type:

* SMS (with media, e.g. MMS)
* Email
* Webhook GET
* Push notifications

Video of any triggered event can be captured and stored in Viam data management via a video storage camera (configured as a dependency).

Actions can also be configured that occur either:

* X seconds after an event is triggered
* Based on an SMS response

Configured actions are methods and payloads on other configured Viam resources.
Currently only generic components/services, sensor components, and vision services are supported.
Example action: An end user that receives an alert SMS can respond responds with '1', which activates a Kasa switch via a component do_command() call.

Triggered events can be queried and deleted with this module.

![](./event-manager-state.png)

## Sensor API

The event-manager resource implements the [rdk sensor component API](https://github.com/viamrobotics/api/blob/main/proto/viam/component/sensor/v1/sensor.proto).

### do_command()

Examples:

```python
await em.do_command({"get_triggered": {"number": 5, "organization_id": "adasdsadasw"}}) # get 5 most recent triggered across all configured events
await em.do_command({"get_triggered": {"number": 5, "event": "Pets out at night", "organization_id": "adasdsadasw"}}) # get 5 most recent triggers for event "Pets out at night"

await em.do_command({"delete_triggered": {"id": "FRgcwnOTZl4FEXiLG7p1KLcpmSX", "location_id": "dsafadad", "organization_id": "adasdsadasw"}}) # delete triggered event based on ID

await em.do_command({"trigger_event": {"event": "Unexpected person"}}) # manually trigger the "Unexpected person" event
await em.do_command({"pause_triggered": {"event": "Unexpected person"}}) # pause actioning on the triggered "Unexpected person" event
await em.do_command({"respond_triggered": {"event": "Unexpected person", "response": "2"}}) # respond "2" to the triggered "Unexpected person" event

```

#### get_triggered

Return details for triggered events in the following format:

```json
{ "triggered": 
    [
        {
            "event": "Unexpected person",
            "time": 1703172467,
            "video_id": "edc519e5-85fe-42ab-af3c-506fcc827948",
            "organization_id": "72ff9713-adc7-4b15-a95b-2174468bde19",
            "location_id": "x7ahxaMJEfF",
            "triggered_camera": "cam1"
        }
    ] 
}
```

Note that video_id is the ID of the corresponding video in Viam's Data Management, if one was saved.

The following arguments are supported:

*organization_id* string (required)

Organization ID for the events

*number* integer

Number of triggered to return - default 5

*event* string

Name of configured event name to return triggered for.  If not specified, will return triggered across all events.

#### delete_triggered_video

Delete a triggered event by video ID

```json
{
  "id": "<event_id",
  "location_id": "<location_id>",
  "organization_id": "<org_id>"
}
```

The following arguments are supported and required:

*id* string

The event video ID.

*location_id* string

Location ID for the event to delete.

*organization_id* string

Organization ID for the event to delete.

#### trigger_event

Manually trigger an event by event name.

```json
{
    "event": "<name of event>"
}
```

#### pause_triggered

Pause a actioning on a triggered event by event name for the remainder of [pause_alerting_on_event_secs](#pause_alerting_on_event_secs).

```json
{
    "event": "<name of event>"
}
```

#### respond_triggered

Respond to a triggered event by event name with response text.

```json
{
    "event": "<name of event>",
    "response": "<response text>"
}
```

### get_readings()

get_readings() JSON returns the current state of events:

``` json
{
    "state": 
    {
        "a person camera 1": {
            "state": "actioning",
            "last_triggered": "2024-10-04T19:59:45Z",
            "triggered_label": "Person",
            "triggered_camera": "cam1",
            "triggered_rules": [
                {
                    "resource": "cam1",
                    "triggered": true,
                    "value": "Person"
                }
            ],
            "actions_taken": [
                {
                    "resource": "kasa_plug_1",
                    "method": "do_command",
                    "response_match": "2",
                    "when": "2024-10-04T19:59:46Z",
                    "payload": "{'action' : 'toggle_on'}"
                }
            ]
        }
    }
}
```

Note that if Viam data capture is enabled for the Readings() method, tabular data will be captured in this format for any triggered events.
This is required in order to use the do_command() get_triggered command.
*app_api_key* and *app_api_key_id* must also be configured for get_triggered to be available.

If "include_dot": true is passed as an "extra" parameter, a [DOT string](https://graphviz.org/doc/info/lang.html) representing a state diagram will be returned with the key "dot".

## Viam event-manager Service Configuration

The service configuration uses JSON to describe rules around events.
The following example configures three events:

* The first triggers when the system is "active" and a configured sensor component gets values of a length greater than 3 at "big.good" within the get_readings() results, sending an email.
* The second triggers when the system is "active" and a configured detector Vision service sees a "Person", sending an SMS and email, and turning on a kasa plug immediately.
* The third triggers when the system is "active" and a configured tracker Vision service sees a "new-object-detected", sending an SMS and email, then turning on a kasa plug in 30 seconds or if an SMS response '1' is received.
If an SMS response of 2 is received, the kasa plug is turned off and the person detected is labeled.  If an SMS response of '3' is received, the kasa switch is turned off.
Video is captured starting 10 seconds before the event (ending 10 seconds after).

```json
{
    "mode": "active",
    "mode_override": {
        "mode": "inactive",
        "until": "2024-11-18T19:05:05Z"
    },
    "back_state_to_disk": true,
    "data_directory": "/data/viam/event_manager",
    "app_api_key": "daifdkaddkdfhshfeasw",
    "app_api_key_id": "weygwegqeyygadydagfd",
    "email_module": "shared-alerting:email",
    "sms_module": "shared-alerting:sms",
    "push_module": "shared-alerting:push",
    "resources": {
        "kasa_plug_1": {"type": "component", "subtype": "generic"},
        "kasa_plug_2": {"type": "component", "subtype": "generic"},
        "cam1": {"type": "component", "subtype": "camera"},
        "vcam1": {"type": "component", "subtype": "camera"},
        "tracker1": {"type": "service", "subtype": "vision"},
        "person_detector": {"type": "service", "subtype": "vision"},
        "stuff_sensor": {"type": "component", "subtype": "sensor"}
    },
    "events": [
        {
            "name": "more than 3 results",
            "modes": ["active"],
            "pause_alerting_on_event_secs": 300,
            "detection_hz": 1,
            "trigger_sequence_count": 2,
            "rule_logic_type": "AND",
            "rules": [
                {
                    "type": "call",
                    "resource": "stuff_sensor",
                    "method": "get_readings",
                    "result_path": "big.good",
                    "result_function": "len",
                    "result_operator": "gt",
                    "result_value": 3,
                    "inverse_pause_secs": 900
                }
            ], 
            "notifications": [
                    {"type": "email", "to": ["test@somedomain.com"], "preset": "alert"}
                ]
        },
        {
            "name": "a person camera 1",
            "modes": ["active"],
            "pause_alerting_on_event_secs": 300,
            "detection_hz": 5,
            "trigger_sequence_count": 2,
            "require_rule_reset": true,
            "rule_reset_count": 3,
            "rule_logic_type": "AND",
            "rules": [
                {
                    "type": "detection",
                    "confidence_pct": 0.6,
                    "class_regex": "Person",                    
                    "camera": "cam1",
                    "detector": "person_detector"
                }
            ], 
            "notifications": [
                    {"type": "sms", "to": ["123-456-7890"], "preset": "alert"},
                    {"type": "email", "to": ["test@somedomain.com"], "preset": "alert"},
                    {"type": "push", "fcm_tokens": ["<FCM_TOKEN_1>", "<FCM_TOKEN_2>"], "preset": "alert", "include_image": true}
                ],
            "actions": [
                {   
                    "when_secs": 0, 
                    "resource": "kasa_plug_1",
                    "method": "do_command",
                    "payload": "{'action' : 'toggle_on'}"
                }
            ]
        },
        {
            "name": "a new person camera 2",
            "modes": ["active"],
            "capture_video" : true,
            "video_capture_resource": "vcam1",
            "event_video_capture_padding_secs": 10,
            "detection_hz": 2,
            "pause_alerting_on_event_secs": 120,
            "rule_logic_type": "AND",
            "rules": [
                {
                    "type": "tracker",
                    "camera": "cam1",
                    "tracker": "cam1",
                    "pause_on_known_secs": 900
                }
            ], 
            "notifications": [{"type": "sms", "to": ["test@somedomain.com"], "include_image": false, "preset": "alert"}],
            "actions": [
                {   
                    "response_match": "1",
                    "when_secs": 60, 
                    "resource": "kasa_plug_2",
                    "method": "do_command",
                    "payload": "{'action' : 'toggle_on'}"
                },
                {   
                    "response_match": "(2|3)",
                    "when_secs": -1, 
                    "resource": "kasa_plug_2",
                    "method": "do_command",
                    "payload": "{'action' : 'toggle_off'}"
                },
                {   
                    "response_match": "2",
                    "when_secs": -1, 
                    "resource": "vcam1",
                    "method": "do_command",
                    "payload": "{'relabel' : {'<<triggered_label>>': 'Known person'}}"
                }
            ]
        }
    ]
}
```

### mode

*enum active|inactive (default: "inactive")*

Event manager mode, which is used in event evaluation based on configured event [modes](#modes)

### mode_override

*object*

If configured, will override the configured [mode](#mode) with *mode* until the date/time specified in *until* (as an ISO8601 UTC datetime string) is passed.
This can be used for delayed activation, temporary activation, etc.

### camera_config

*object (required)*

An object containing configured physical camera component names as keys, and object values with:

*video_capture_camera* - The name of the associated configured video capture camera for the physical camera.

*vision_service*  - The name of the associated configured vision service to use.

### resources

*object*

These are the associated resources to import and dependencies to use with the action and event rules.
The key is the name of the configured resource, with object containing:

*type* - the resource type: component or service.
*subtype* - the resource subtype - currently only 'generic' and 'vision' are supported for actions, for rules the types are context-specific by rule type.

### app_api_key

*string (optional)*

Used to interface with Viam data management for triggered event management.
Required if using [do_command](#do_command) functionality.

### app_api_key_id

*string (optional)*

Used to interface with Viam data management for triggered event management.
Required if using [do_command](#do_command) functionality.

### enable_backoff_schedule

*boolean (default: false)*

When enabled, the module's global backoff schedule will be applied to all events that do not have their own `backoff_schedule` defined, and event-specific backoff schedules will be be applied.

### backoff_schedule

*object*

A top-level object that overrides the module's default backoff schedule. This schedule is applied to all events when `enable_backoff_schedule` is true and the event does not have its own `backoff_schedule`. The module's default is:
```json
{
  "300": 120,
  "1200": 300,
  "3600": 900
}
```

### email_module

*string (optional)*

The name of an email sending service configured as part of this machine that uses the API format of [this module](https://app.viam.com/module/mcvella/sendgrid-email)
If email notifications are configured, this is required.

### sms_module

*string (optional)*

The name of an SMS sending service configured as part of this machine that uses the API format of [this module](https://app.viam.com/module/mcvella/twilio-sms)
If SMS notifications are configured, this is required.

### push_module

*string (optional)*

The name of a push notification service configured as part of this machine (e.g., one compatible with [Datiom/viam-firebase-push](https://github.com/Datiom/viam-firebase-push)).
If push notifications of type `push` are configured, this module is required. It will receive a `do_command` with parameters `fcm_tokens`, `preset`, and `template_vars`.

### back_state_to_disk

*boolean (default: false)*

When enabled, the event manager will persist the state of events to disk using SQLite. This allows the event manager to restore its state after a restart, ensuring that triggered events, paused events, and action statuses are maintained across restarts.

The following state information is persisted for each event:

* Triggered status
* Last triggered timestamp
* Current event state (monitoring, triggered, actioning, paused)
* Pause reason and duration
* Triggered camera and label information
* Action statuses and timestamps

State is saved automatically when:

* Events are triggered
* Actions are taken
* The event manager is reconfigured
* Every few minutes during normal operation

If an event is removed from the configuration, its state will not be restored. This ensures that configuration changes are handled safely.

### data_directory

*string (default: "/tmp/viam/event_manager")*

The directory where state data will be stored when `back_state_to_disk` is enabled. The SQLite database will be created as `{name}_events.db` in this directory, where `{name}` is the name of the event manager component.

### events

*list*

Any number of events can be configured, and will be repeatedly evaluated as long as *pause_alerting_on_event_secs* is not currently being enforced.
If an event evaluates to true, a video save request occurs and any configured notifications will occur.

#### name

*string (required)*

Label for the configured event.
Used in logging and notifications.

#### modes

*list[enum home|away] (required)*

The list of modes in which this event will be evaluated.

#### capture_video

*boolean (default false)*

If enabled and a *video_capture_resource* is configured, video will be captured for triggered events.

#### video_capture_resource

*string*

The name of a video capture resource, must also be specified in *resources* 

#### pause_alerting_on_event_secs

*integer (default 60)*

How long to pause after triggered event before rules for the event are again evaluated.

#### event_video_capture_padding_secs

*integer (default 10)*

For stored video, how many seconds before and after the event should be saved (for example, a value of 10 would mean 20 seconds of video would be stored).

#### backoff_schedule

*object*

An optional, event-specific dictionary that overrides the global backoff schedule. For this schedule to be active, the top-level `enable_backoff_schedule` attribute must be set to `true`.

The schedule is a dictionary where keys are the number of seconds since the first trigger in a continuous sequence, and values are the new pause duration in seconds.

Example:
```json
"backoff_schedule": {
  "300": 120,   
  "1200": 300,
  "3600": 900
}
```
In this example:
1. The event starts with the `pause_alerting_on_event_secs` setting
2. If the event is still continously triggered after 5 minutes, the pause duration becomes 120 seconds (2 min)
3. If the event is still continously triggered again after 20 minutes, the pause duration becomes 300 seconds (5 min)
4. If the event is still continously triggered again after 1 hour, the pause duration becomes 900 seconds (15 min)

This helps manage alert frequency by gradually increasing the pause duration as the event continues to trigger.

#### detection_hz

*integer (default 5)*

How often rules are evaluated, best effort.

#### rule_logic_type

*enum AND|OR|XOR|NOR|NAND|XNOR (default AND)*

The [logic gate](https://www.techtarget.com/whatis/definition/logic-gate-AND-OR-XOR-NOT-NAND-NOR-and-XNOR) to use with configured rules.
For example, if *NOR* was set and there were two rules configured that both evaluated false, the event would trigger.

#### trigger_sequence_count

*integer (default 1)*

How many times in a row an event must be evaluate as true in order to be considered triggered.
For example, you may want to get 3 detections in a row that it is an unknown person.
This can help alleviate some false positives.

#### require_rule_reset

*boolean (default false)*

When enabled, an event that has been triggered will not trigger again until:
1. Its rules evaluate to false for the specified number of times (`rule_reset_count`)
2. Then subsequently evaluate to true again

This is useful for detecting true state changes rather than continuous states. For example, detecting when someone sits at a desk, then leaves, then returns - rather than continuously triggering while they remain at the desk.

#### rule_reset_count

*integer (default 1)*

Used with `require_rule_reset`. Specifies how many consecutive times the rules must evaluate to false before the event can be re-triggered.
Higher values can prevent false resets due to momentary fluctuations or detection errors.

#### notifications

*list*

Notifications when an event triggers.

"type" is one of sms|email|webhook_get|push.

"preset" is a string specifying the name of the preset message to send.

"to" is a list of phone numbers or email addresses.

"include_image" - whether to include an image of the event (if available) in the notification. Default is true for SMS, false for email and push.

"url" - for webhook_get, the URL to call.

"fcm_tokens" - for push notifications, a list of Firebase Cloud Messaging tokens for target devices.

The following are also sent in a *template_vars* object for sms and email:

"event_name" - The configured event name.

"triggered_label" - For computer vision triggers, the triggered label/class.

"triggered_camera" -  For computer vision triggers, the triggered camera.

The following are also sent in the *template_vars* object for email and push (if include_image is true):

"media_base64" - For computer vision triggers, the base64 string representation of the image.

"media_mime_type" - For computer vision triggers, the MIME type of the image.

For push notifications, a `data` object is also included in the notification payload that can be used by the receiving app for deep linking. The data object includes:
- type: "camera_event"
- cameraName: The name of the camera that triggered the event

#### actions

*list*

A list of objects containing:

"resource" - The name of a configured action resource.
Currently only "generic" components and services, sensor components, and vision services are supported.

"method" - The resource method to call

"payload" - The JSON payload to pass to the method.
Pass as a string that will be decoded to JSON.
Single quotes will get translated to double quotes so as to validate as proper JSON.
The following can variables be included enclosed in```<<>>``` (for example ```<<triggered_label>>```) and replaced with the corresponding value:

* event_name: The **name** of the event that was triggered.
* triggered_label: If the event was triggered via a computer vision service, this is the label/class that triggered the event.

"response_match" -  If a response is sent via doCommand (or via SMS response) that matches "response_match" (regex), then this and any other matching actions will be taken.
Any other actions that could later be taken will be ignored until the event triggers again.

"when_secs" - How many seconds after the event triggers should the action occur.
If not specified or set to 0, will happen immediately.
If set to -1, will not happen unless response_match causes it to occur.

#### rules

*list*

Rules define what is evaluated in order to trigger event logging and notifications.
Any number of rules can be configured for a given event.

##### rule type

*enum detection|classification|tracker|time*

If *type* is **detection**, *camera* (a configured camera included in *resources*), *confidence_pct* (percent confidence threshold out of 1), and *class_regex* (regular expression to match detection class/label, defaults to any class) must be defined. The system will first call `get_image()` on the camera component and then use the detector service's `get_detections()` method with that image.

If *type* is **classification**, *camera* (a configured camera included in *resources*), *confidence_pct* (percent confidence threshold out of 1), and *class_regex* (regular expression to match detection class/label, defaults to any class) must be defined. The system will first call `get_image()` on the camera component and then use the classifier service's `get_classifications()` method with that image.

If *type* is **tracker**, a *tracker* vision service, and a *camera* (a configured camera included in *resources*) must be defined. *pause_on_known_secs* may be specified, which is the number of seconds to pause event evaluation if a known person is seen. The tracker rule uses `capture_all_from_camera()` method directly.

For all these vision rule types, an optional *extra* dictionary can be specified. This dictionary is passed as the `extra` parameter to the relevant vision service method calls, allowing additional configuration options to be passed to the vision service.

Example rule with extra parameter:
```json
{
    "type": "detection",
    "camera": "cam1",
    "detector": "person_detector",
    "class_regex": "Person",
    "confidence_pct": 0.7,
    "extra": {
        "threshold": 0.4,
        "max_detections": 5
    }
}
```

If *type* is **time**, *ranges* must be defined, which is a list of *start_hour* and *end_hour*, which are integers representing the start hour in UTC.

If *type* is **call**, a *resource* configured in [resources](#resources) must be specified (currently generic components/services, vision services, sensor components, and motor components are supported), as well as the following other parameters:

| Key | Type | Inclusion | Description |
| ---- | ---- | --------- | ----------- |
| `method` | string | **Required** |  The method name to call against the configured resource. |
| `payload` | string | **Required** |  Optional JSON payload to pass to the specified method. |
| `result_path` | string | Optional |  The path, in javascript dot notation, of the property to access. |
| `result_function` | string | Optional | A python function to call on the result.  Currently supported: len, any |
| `result_operator` | string | **Required** | A operator to evaluate against the result.  Currently supported: eq, ne, lt, lte, gt, gte, regex, in, hasattr. |
| `result_value` | string | **Required** | The value to use in the operator evaluation. |
| `inverse_pause_secs` | string | Optional | A duration to pause event evaluation if the result evaluates to false. |

Example motor action that sets motor power to 100% immediately:
```json
{
    "resource": "my_motor",
    "method": "set_power",
    "payload": "1",
    "when_secs": 0
}
```

## Building and running

This project is set up to be build with pyinstaller, which can be run by calling:

``` bash
sh build.sh
```

To run locally, point to the binary at:

``` bash
dist/main
```