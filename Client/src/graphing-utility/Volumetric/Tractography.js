import * as THREE from "three";
import React from "react";

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