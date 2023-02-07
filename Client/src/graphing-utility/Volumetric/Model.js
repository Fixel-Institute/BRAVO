import React from "react";

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
    <meshPhongMaterial transparent opacity={material.opacity} color={material.color} specular={material.specular} shininess={material.shininess} />
  </mesh>
};

export default Model;