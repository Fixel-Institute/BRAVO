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

function CoordinateSystem({length, origin}) {
  const xDir = new THREE.Vector3(-1, 0, 0);
  const yDir = new THREE.Vector3(0, 0, 1);
  const zDir = new THREE.Vector3(0, 1, 0);

  const centroid = new THREE.Vector3(origin[0], origin[1], origin[2]);
  
  return [
    <arrowHelper key={"xdir"} args={[xDir, centroid, length, "#FF0000"]} />,
    <arrowHelper key={"ydir"} args={[yDir, centroid, length, "#00FF00"]} />,
    <arrowHelper key={"zdir"} args={[zDir, centroid, length, "#0000FF"]} />,
  ]
}

export default CoordinateSystem;