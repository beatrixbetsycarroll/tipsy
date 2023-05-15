import asyncio

from viam.robot.client import RobotClient
from viam.rpc.dial import Credentials, DialOptions
from viam.components.base import Base
from viam.components.camera import Camera
from viam.services.vision import VisionServiceClient, VisModelConfig, VisModelType

from viam.components.sensor import Sensor

from tipsy_helpers import \
    swivel_arbitrary_amount, \
    check_if_any_people_in_view, \
    turn_towards_center_of_person, \
    move_forward_safely, \
    pause_for_a_moment, \
    turn_a_little_to_the_right, \


async def connect():
    creds = Credentials(
        type='robot-location-secret',
        payload='593swwv9gedfr8xbwf6n9qkyzorqv8ryu7fl9o47r8iudx5q')
    opts = RobotClient.Options(
        refresh_interval=0,
        dial_options=DialOptions(credentials=creds)
    )
    return await RobotClient.at_address('empty-pine-main.ot97v3aaze.viam.cloud', opts)


async def main():
    robot = await connect()
    rover_base = Base.from_robot(robot, 'viam_base')
    camera = Camera.from_robot(robot, "my-camera")

    # Get and set up the Vision Service
    vision = VisionServiceClient.from_robot(robot)
    params = {"model_path": "./effdet0.tflite", "label_path": "./labels.txt", "num_threads": 1}
    personDet = VisModelConfig(name="person_detector", type=VisModelType("tflite_detector"), parameters=params)
    await vision.add_detector(personDet)
    names = await vision.get_detector_names()
    print(names)

    ultrasonic_sensor = Sensor.from_robot(robot, "ultrasonic")

    # N is number of times we will be running thru the control loop
    N = 200

    # Start control loop wherein we will look for objects, and move accordingly
    for i in range(N):

        swivel_arbitrary_amount(rover_base)
        person_found = check_if_any_people_in_view(camera, vision)
             
        if person_found:
            d, image = person_found
            turn_towards_center_of_person(rover_base, d, image)
            move_forward_safely(rover_base, ultrasonic_sensor)
            print("Any nearby people: feel free to grab a drink!")
            pause_for_a_moment()
        else:
            print("No thirsty people in this direction!")
            print("I'll check around a bit here before I spin again!")
            search_attempt_counter = 0
            while search_attempt_counter < 4:
                turn_a_little_to_the_right()
                person_found = check_if_any_people_in_view(camera, vision)
                if person_found:
                    d, image = person_found
                    turn_towards_center_of_person(rover_base, d, image)
                    move_forward_safely(rover_base, ultrasonic_sensor)
                    print("Any nearby people: feel free to grab a drink!")
                    pause_for_a_moment()
                else:
                    search_attempt_counter+=1


    await asyncio.sleep(5)
    await robot.close()

if __name__ == '__main__':
    asyncio.run(main())
