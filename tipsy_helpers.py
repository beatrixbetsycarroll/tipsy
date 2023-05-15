from random import randint
from time import sleep



async def swivel_arbitrary_amount(base):
    # randomly choose an amount to turn. 
    # -180 would be a counter-clockwise about-face, 
    # and 180 would be a clockwise about-face.
    amount_to_turn = randint(-180, 180)
    await base.spin(velocity=100, angle=amount_to_turn)
    print(f"spinning {amount_to_turn} degrees")

async def make_sure_nothing_too_close(sensor):
    coast_is_clear = False
    sensor_result = await sensor.get_readings()
    distance = sensor_result["distance"]
    if distance > 1:
        coast_is_clear = True
    return coast_is_clear

async def move_forward_safely(base, sensor):
    coast_is_clear = make_sure_nothing_too_close(sensor)
    while coast_is_clear:
        # moves the Viam Rover forward 500mm at 500mm/s
        await base.move_straight(velocity=500, distance=500)
        coast_is_clear = make_sure_nothing_too_close(sensor)
    # TODO: In later versions I would edit this function so movement can be smoother... 
    # maybe use velocity info to try to make it so it does not stop 
    # but is still almost perfectly "safe", if poss

async def move_forward_safely_for_specified_distance(base, sensor, desired_distance):
    remaining_distance = desired_distance

    coast_is_clear = make_sure_nothing_too_close(sensor)
    while coast_is_clear and (remaining_distance > 0):
        await base.move_straight(velocity=500, distance=500)
        remaining_distance -= 500 
        coast_is_clear = make_sure_nothing_too_close(sensor)

async def turn_a_little_to_the_right(base):
    await base.spin(velocity=100, angle=15)

async def check_if_any_people_in_view(camera, vision):
    image = await camera.get_image()
    detections = await vision.get_detections(image, "person_detector")
    person_found = False
    for d in detections:
        if d.confidence > 0.8:
            print(d)
            print()
            if d.class_name.lower() == "person":
                print("This is a person!")
                person_found = d, image
                return person_found
                # because we know that there is at least one person in view,
                # we can stop looping thru the detections early 

async def pause_to_serve_drinks():
    # Pause for half a minute to allow people to grab a beer
    sleep(30)

# TODO: make a function here that can be called to inject randomness into how it walks

async def turn_towards_center_of_person(base, d, frame):
    # I am going to assume that the camera sees the center 2/3 of
    # everything in front of him (I am assuming its not a fisheye lens where the entire 
    # periphery is in view so this seems reasonable based on my experience with cameras)

    # This means I am going to assume that the visual field in the image covers a span of 120 degrees
    # meaning, from -60 degrees to 60 degrees,
    # i.e.: from robot's 10 o'clock to robot's 2 o'clock  

    percentage_of_horizon_that_camera_covers = 2/3
    camera_angle_span = percentage_of_horizon_that_camera_covers * 90
    # (camera_angle_span comes out to be 60 here, by design)

    # Now I want to calculate "amount_to_turn" as my approximation of how many 
    # degrees the robot should turn to get closer to facing the person head on.

    # I came up with this proportion:

        #   (d_x_center - frame_x_center)       =           amount_to_turn
        # _________________________________     =   ____________________________________
        #     (frame_width - d_width)                  camera_angle_span // a.k.a. 60

    # ...to represent, essentially, this relationship:

        # [how far off from center the object is] = [how much the robot should turn, 
        #                                            with (+/-)60 degrees being the extremes]

    # I use the above proportion to calculate "amount_to_turn":

    d_width = d.x_max - d.x_min
    d_x_center = d.x_min + (d.x_max - d.x_min)/2

    frame_width = frame.x_max - frame.x_min
    frame_x_center = frame.x_min + (frame.x_max - d.x_min)/2

    amount_to_turn  = (d_x_center - frame_x_center) * camera_angle_span \
        / (frame_width - d_width)

    # I want amount_to_turn to be in range(-60,60) to be consistent 
    # with how the rover takes "spin" instructions 
    # (and with what I have assumed about the camera) 

    await base.spin(velocity=100, angle=amount_to_turn)


async def take_a_step_back(base):
    # move backward briskly if Tipsy is falling backwards,
    # like taking a quick step back when when pushed backwards

    # moves the Viam Rover backward 200mm (aka 8in) at 1400mm/s (aka avg walking speed)
    await base.move_straight(velocity=1400, distance=-100)



# NOTE: EXTRA CREDIT: 
# Question:
#       How might you deal with Tipsy running into an object and starting to 
#       tip backwards (perhaps if the object was not in the field of detection 
#       for the ultrasonic sensor)?
# 
# My answer:
# 
# We could call my take_a_step_back function (or one very similar with 
# different velocity and distance) if Tipsy is has run into an object and 
# is starting to tip backwards.
# 
# That still leaves the question of "how would tipsy know its run 
# into something and is now tipping backward?"
# 
# I see that viam has this class:
# https://python.viam.dev/autoapi/viam/components/movement_sensor/index.html#viam.components.movement_sensor.Orientation
# on the movement_sensor component! If this robot had a movement sensor, I would think we could use that class
# to:
#   get the z_axis orientation
#   wait a few seconds
#   get the z_axis orientation again
#   if it has changed such that it seems to be tipping backward, 
#   then call take_a_step_back
# still, I am not sure the best way to monitor for that kind of change.
# we would want to be checking that orientation data quickly enough and frequently enough 
# that it would actually be useful, and yet also not make it so frequent that the computation
# tax is not worth it.
