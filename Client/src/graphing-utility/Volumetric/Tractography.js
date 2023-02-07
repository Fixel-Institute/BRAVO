import * as THREE from "three";
import React from "react";

/**
 * Wrapper for creating a line from buffer geometry 
 *
 * @param {number[][]} pointArray - Array of connected points in 3D space.
 * @param {string} color - Hex-encoded color string
 * @param {number} linewidth - Currently linewidth is useless on browser due to WebGL limitation
 * @param {THREE.Matrix4} matrix - Transformation matrix for the mesh object.
 * 
 * @return {line} Line object to be rendered.
 */
function Tractography({pointArray, color, linewidth, matrix}) {
  const points = [];
  for (var point of pointArray) {
    points.push(point[0], point[1], point[2] || 0);
  };

  return <line matrixAutoUpdate={false} matrix={matrix}>
    <bufferGeometry attributes={{
      position: new THREE.Float32BufferAttribute(points, 3)
    }}/>
    <lineBasicMaterial color={color} linewidth={linewidth}/>
  </line>
}

export default Tractography;