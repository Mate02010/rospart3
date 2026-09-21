cmake_minimum_required(VERSION 3.20)
project(robotica_part3)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch description config worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
