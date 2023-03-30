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

function ShadowLight({x, y, z, color, intensity}) {
  const d = 1;
  const orthoCamera = new THREE.OrthographicCamera(-d, d, d, -d, 1, 4)
  return <directionalLight args={[color, intensity]} position={[x, y, z]} castShadow shadow={{bias: -0.002, camera: orthoCamera}} />;
}

export default ShadowLight;