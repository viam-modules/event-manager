# event-manager modular service

*event-manager* is a Viam modular component that provides eventing capabilities using the generic component API.

The model this module makes available is viam-soleng:generic:event-manager

The event manager is normally used in conjunction with a mobile app, which provides a user interface for configuring events, viewing camera feeds, and viewing alerts.

The event manager can be configured to looks for rules being triggered, based on:

* Time of day
* Computer vision detections
* Computer vision classifications
* Computer vision tracker events (new person seen that is not an approved person)

When a rule is triggers, notification actions can occur of type:

* SMS (with media, e.g. MMS)
* Email
* GET push notification

Video of any triggered event is captured and stored in Viam data management.

Events can also be escalated via SMS response - for example, an end user that receives an alert SMS can respond to escalate, which can trigger actions like turning on lights and/or alarms.

Triggered events can be queried and cleared with this module.

## Prerequisites

None

## API

The event-manager resource implements the [rdk generic API](https://github.com/viamrobotics/api/blob/main/proto/viam/component/generic/v1/generic.proto).

### do_command()

Examples:

```python
await em.do_command({"get_triggered": {"number": 5}}) # get 5 most recent triggered across all configured events
await em.do_command({"get_triggered": {"number": 5, "camera": "ipcam"}}) # get 5 most recent triggered for "ipcam" across all configured events
await em.do_command({"get_triggered": {"number": 5, "event": "Pets out at night"}}) # get 5 most recent triggers for event "Pets out at night"

await em.do_command({"clear_triggered": {}}) # clear all triggered cross all configured events
await em.do_command({"clear_triggered": {"id": "SAVCAM--my_event--ipcam--1705448784"}}) # clear a specific triggered event
await em.do_command({"clear_triggered": {"camera": "ipcam"}}) # clear all triggered for "ipcam" across all configured events
await em.do_command({"clear_triggered": {"event": "Pets out at night"}}) # clear all triggered for event "Pets out at night"
```

#### get_triggered

Return details for triggered events in the following format:

```json
{ "triggered": 
    [
        {
            "event": "Unexpected person",
            "camera": "cam1",
            "time": 1703172467,
            "id": "Unexpected_person_cam1_1703172467"
        }
    ] 
}
```

Note that "id" can be passed to a properly configured Viam [image-dir-cam](https://app.viam.com/module/viam-labs/image-dir-cam) as the "dir" *extra* param in order to view the captured camera stream.

The following arguments are supported:

*number* integer

Number of triggered to return - default 5

*camera* string

Name of camera to return triggered for.  If not specified, will return triggered across all cameras.

*event* string

Name of event to return triggered for.  If not specified, will return triggered across all events.

#### clear_triggered

Clear triggered events, returning results details in the following format:

```json
{
  "total": 10
}
```

The following arguments are supported:

*camera* string

Name of camera to delete triggered for.  If not specified, will delete triggered across all cameras.

*event* string

Name of event to delete triggered for.  If not specified, will delete triggered across all events.

*id* string

ID of event to delete triggered for. If not specified, will delete triggered across all events and cameras (depending on what is passed for *event* and *camera*)

## Viam Service Configuration

The service configuration uses JSON to describe rules around events.
The following example configures two events that trigger when an configured Vision service sees a "new-object-detected", sending an SMS and email, then turning on a kasa plug if escalated.

```json
{
    "mode": "active",
    "pause_known_person_secs": 3600,
    "pause_alerting_on_event_secs": 300,
    "event_video_capture_padding_secs": 10,
    "detection_hz": 5,
    "camera_config": {
        "cam1" : { "video_capture_camera": "vcam1", "vision_service": "tracker1" },
        "cam2" : { "video_capture_camera": "vcam2", "vision_service": "person_detector" },
    },
    "action_resources": {
        "kasa_plug_1": {"type": "component", "subtype": "generic"},
        "kasa_plug_2": {"type": "component", "subtype": "generic"},
        "vcam1": {"type": "service", "subtype": "vision"}
    },
    "notifications": {
        "email": ["test@somedomain.com"],
        "sms": ["123-456-7890"]
    },
    "sms_module": "sms",
    "email_module": "email",
    "events": [
        {
            "name": "new person camera 1",
            "modes": ["active"],
            "rule_logic_type": "AND",
            "rules": [
                {
                    "type": "tracker",
                    "cameras": ["vcam1"]
                }
            ], 
            "notifications": [{"type": "sms", "preset": "alert"}, {"type": "email", "preset": "alert"}],
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
            "name": "new person camera 2",
            "modes": ["active"],
            "rule_logic_type": "AND",
            "rules": [
                {
                    "type": "detection",
                    "confidence_pct": 0.6,
                    "class_regex": "Person",                    
                    "cameras": ["vcam2"]
                }
            ], 
            "notifications": [{"type": "sms", "preset": "alert"}, {"type": "email", "preset": "alert"}],
            "actions": [
                {   
                    "sms_match": "1",
                    "when_secs": 60, 
                    "resource": "kasa_plug_2",
                    "method": "do_command",
                    "payload": "{'action' : 'toggle_on'}"
                },
                {   
                    "sms_match": "(2|3)",
                    "when_secs": -1, 
                    "resource": "kasa_plug_2",
                    "method": "do_command",
                    "payload": "{'action' : 'toggle_off'}"
                },
                {   
                    "sms_match": "2",
                    "when_secs": -1, 
                    "resource": "vcam1",
                    "method": "do_command",
                    "payload": "{'relabel' : {'<label>': 'Known person'}}"
                }
            ]
        }
    ]
}
```

### mode

*enum active|inactive (default: "inactive")*

Event manager mode, which is used in event evaluation based on configured event [modes](#modes)

### events

*list*

Any number of events can be configured, and will be repeatedly evaluated.
If an event evaluates to true, it will be tracked, and any configured notifications will occur.

### name

*string (required)*

Label for the configured event.
Used in logging and notifications.

#### modes

*list[enum home|away] (required)*

The list of modes in which this event will be evaluated.

#### rule_logic_type

*enum AND|OR|XOR|NOR|NAND|XNOR (default AND)*

The [logic gate](https://www.techtarget.com/whatis/definition/logic-gate-AND-OR-XOR-NOT-NAND-NOR-and-XNOR) to use with configured rules.
For example, if *NOR* was set and there were two rules configured that both evaluated false, the event would trigger.

#### notifications

*list*

Notifications types when an event triggers.

"type" is one of sms|email.

"preset" is a string specifying the name of the preset message to send.

##### actions

*list (required)*

A list of objects containing:

"resource" - the name of a configured action resource.
Currently only "generic" components and services, as well as vision services are supported.

"method" - the resource method to call

"payload" - the JSON payload to pass to the method

#### rules

*list*

Rules define what is evaluated in order to trigger event logging and notifications.
Any number of rules can be configured for a given event.

##### rule type

*enum detection|classification|tracker|time*

If *type* is **detection**, *cameras* (list of configured cameras), *confidence_pct* (percent confidence threshold out of 1), and *class_regex* (regular expression to match detection class, defaults to any class) must be defined.

If *type* is **classification**, *cameras* (list of configured cameras), *confidence_pct* (percent confidence threshold out of 1), and *class_regex* (regular expression to match detection class, defaults to any class) must be defined.

If *type* is **tracker**, *cameras* (list of configured cameras) must be defined.

If *type* is **time**, *ranges* must be defined, which is a list of *start_hour* and *end_hour*, which are integers representing the start hour in UTC.

## Todo

* Support other types of webhooks
