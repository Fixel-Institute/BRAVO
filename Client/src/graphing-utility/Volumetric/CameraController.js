import React from "react";

import { useThree } from '@react-three/fiber'

import { ArcballControls } from "three/examples/jsm/controls/ArcballControls"
import { TrackballControls, OrbitControls } from "@react-three/drei";

/**
 * Wrapping Camera Controller from React-three/drei library. The default 
 * min distance is 20 and max distance 500. Not dynamically adjustable but can 
 * be manually adjusted in the source code.
 * 
 * Initial camera position is always looking at origin from -X position (Left lateral direction looking at Brain).
 *
 * @param {boolean} cameraLock - Whether camera will be locked or not.
 * 
 * @return {(null|OrbitControls)} either null if camera is locked or OrbitControls object if camera is available
 */
function CameraController ({cameraLock}) {
  const { camera, scene, gl } = useThree();

  React.useEffect(() => {
    camera.position.set(-200, 0, 0);
    camera.lookAt(0, 0, 0);
  }, []);

  return cameraLock ? null : <OrbitControls makeDefault camera={camera} domElement={gl.domElement} minDistance={20} maxDistance={500} rotateSpeed={2} zoomSpeed={1} panSpeed={0.5} />
};

export default CameraController
