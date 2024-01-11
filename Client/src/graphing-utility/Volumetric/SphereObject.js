/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import * as THREE from "three";
import React from "react";

/**
 * Wrapper for creating a dot from buffer geometry 
 *
 * @param {number[]} pointArray - Array of points in 3D space.
 * @param {string} color - Hex-encoded color string
 * @param {number} size - Size of the Sphere (Radius)
 * @param {THREE.Matrix4} matrix - Transformation matrix for the mesh object.
 * 
 * @return {line} Line object to be rendered.
 */
function SphereObject({pointArray, color, size, matrix}) {
  return <mesh position={[Math.abs(pointArray[0]),-pointArray[1],pointArray[2]]} matrixAutoUpdate={true} matrix={matrix}>
    <sphereGeometry args={[size, 32, 32]} />
    <meshStandardMaterial color={color} />
  </mesh>
}

export default SphereObject;