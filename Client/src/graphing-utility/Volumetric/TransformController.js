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
import { useThree } from "@react-three/fiber";

function TransformController({transformMatrix}) {
  const { scene } = useThree();
  React.useEffect(() => {
    scene.matrixAutoUpdate = false;
    scene.matrixWorld = transformMatrix;
    scene.updateWorldMatrix();
  }, [transformMatrix])
}

export default TransformController;