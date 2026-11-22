cmake_minimum_required(VERSION 3.20)
project(dif_bot)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY description config launch worlds rviz maps
  DESTINATION share/${PROJECT_NAME}
)

file(GLOB SCRIPTS scripts/*.py)
install(
  PROGRAMS ${SCRIPTS}
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
