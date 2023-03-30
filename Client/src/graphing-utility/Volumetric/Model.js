/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React from "react";
import { DoubleSide } from "three";

/**
 * Wrapper for creating a mesh from buffer geometry 
 *
 * @param {Object} geometry - position and normal vectors from STL loader.
 * @param {Object} material - material parameters, include substate like opacity, color, specular, and shininess
 * @param {THREE.Matrix4} matrix - Transformation matrix for the mesh object.
 * 
 * @return {mesh} Mesh object to be rendered.
 */
function Model({geometry, material, matrix}) {
  return <mesh castShadow matrixAutoUpdate={false} matrix={matrix}>
    <bufferGeometry attach="geometry" attributes={{
      position: geometry.position,
      normal: geometry.normal
    }}/>
    <meshPhongMaterial transparent side={DoubleSide} opacity={material.opacity} color={material.color} specular={material.specular} shininess={material.shininess} />
  </mesh>
};

export default Model;