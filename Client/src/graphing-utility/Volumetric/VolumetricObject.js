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

import {
  BoxGeometry,
  Mesh,
  LinearFilter,
  DoubleSide,
  MeshBasicMaterial,
  ClampToEdgeWrapping,
  Vector3,
  DataTexture,
  Matrix4,
} from "three";

import {
  useThree
} from "@react-three/fiber";

import * as math from "mathjs";

function extractSlice(data, dimension, slice_index, axis) {
  switch (axis) {
    case 'x': {
      const slice_data = new Array(dimension[1]*dimension[2]);
      for (var i = 0; i < dimension[1]; i++) {
        for (var j = 0; j < dimension[2]; j++) {
          slice_data[i + j*dimension[1]] = data[slice_index*dimension[1]*dimension[2] + i*dimension[2] + j];
        } 
      }
      return slice_data;
    }

    case 'y': {
      const slice_data = new Array(dimension[0]*dimension[2]);
      for (var i = 0; i < dimension[0]; i++) {
        for (var j = 0; j < dimension[2]; j++) {
          slice_data[i + j*dimension[0]] = data[i*dimension[1]*dimension[2] + slice_index*dimension[2] + j];
        } 
      }
      return slice_data;
    }

    case 'z':
    default: {
      const slice_data = new Array(dimension[0]*dimension[1]);
      for (var i = 0; i < dimension[0]; i++) {
        for (var j = 0; j < dimension[1]; j++) {
          slice_data[i + j*dimension[0]] = data[i*dimension[1]*dimension[2] + j*dimension[2] + slice_index];
        } 
      }
      return slice_data;
    }
  }
}

function colorMapping(value, clim, cmap) {
  switch (cmap) {
    case "grayscale":
    default: {
      const intensity = Math.floor((value - clim[0]) / (clim[1]-clim[0]) * 255);
      return [intensity, intensity, intensity, 255];
    }
  }
}

function createTexture(data, width, height, clim) {
  const size = width * height;
  const cdata = new Uint8Array(4*size);

  for (let i = 0; i < size; i++) {
    const stride = i * 4;
    const color = colorMapping(data[i], clim);
    cdata[stride] = color[0];
    cdata[stride + 1] = color[1];
    cdata[stride + 2] = color[2];
    cdata[stride + 3] = color[3];
  }

  return new DataTexture(cdata, width, height);
}

function getPointerCoordinate(mouse, camera) {
  var vec = new Vector3(); // create once and reuse
  var pos = new Vector3(); // create once and reuse

  vec.set(mouse.x, mouse.y, 0.5);
  vec.unproject( camera );
  return vec;
}

function VolumetricSlice({data, axis, matrix, cameraLock}) {
  const index = data.axisOrder.indexOf(axis);
  const { camera, mouse, viewport } = useThree();

  const [sliceIndex, setSliceIndex] = React.useState(Math.floor(data.dimensions[index]/2));
  const [slice, setSlice] = React.useState(null);
  const [toMoveSlice, setToMoveSlice] = React.useState(false);
  const [startCoordinate, setStartCoordinate] = React.useState(null);

  React.useEffect(() => {
    const sliceBuffer = extractSlice(data.data, data.dimensions, sliceIndex, axis);
    setSlice(sliceBuffer);
  }, [sliceIndex])
  
  function onMouseDown(event) {
    event.stopPropagation();
    if (cameraLock) {
      const pos = getPointerCoordinate(mouse, camera);
      setStartCoordinate(pos);
      setToMoveSlice(true);
    }
  }

  function onMouseUp(event) {
    event.stopPropagation();
    setToMoveSlice(false);
  }

  React.useEffect(() => {
    if (!toMoveSlice) return;

    const mouseMove = (event) => {
      const pos = getPointerCoordinate(mouse, camera);
      const scale = math.norm(math.matrix([camera.position.x, camera.position.y, camera.position.z]));
      if (axis == "x") {
        const newSlice = Math.floor(sliceIndex + (pos["x"]-startCoordinate["x"]) * scale);
        if (newSlice < 0) newSlice = 0;
        if (newSlice >= data.dimensions[index]) newSlice = data.dimensions[index]-1;
        setSliceIndex(newSlice);
      } else if (axis == "y") {
        const newSlice = Math.floor(sliceIndex + (pos["z"]-startCoordinate["z"]) * scale);
        if (newSlice < 0) newSlice = 0;
        if (newSlice >= data.dimensions[index]) newSlice = data.dimensions[index]-1;
        setSliceIndex(newSlice);
      } else if (axis == "z") {
        const newSlice = Math.floor(sliceIndex + (pos["y"]-startCoordinate["y"]) * scale);
        if (newSlice < 0) newSlice = 0;
        if (newSlice >= data.dimensions[index]) newSlice = data.dimensions[index]-1;
        setSliceIndex(newSlice);
      }
    }

    window.addEventListener('mousemove', mouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', mouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    }
  }, [toMoveSlice]);

  if (!slice) return null;

  if (axis == "z") {
    const offset_matrix = new Matrix4();
    offset_matrix.makeTranslation(-data.xRange._data[Math.floor(data.dimensions[0]/2)], -data.yRange._data[Math.floor(data.dimensions[1]/2)], -data.zRange._data[data.dimensions[2]-1]);

    const canvasMap = createTexture(slice, data.dimensions[0], data.dimensions[1], [data.windowLow, data.windowHigh]);
    canvasMap.minFilter = LinearFilter;
    canvasMap.wrapS = canvasMap.wrapT = ClampToEdgeWrapping;
    canvasMap.needsUpdate = true;

    const slice_position = new Matrix4().makeTranslation(0,0,data.zRange._data[sliceIndex]);
    const position = new Matrix4().makeRotationZ(Math.PI).premultiply(offset_matrix).premultiply(matrix).multiply(slice_position);
    return <mesh matrixAutoUpdate={false} matrix={position} onPointerDown={onMouseDown} onPointerUp={onMouseUp}>
      <planeGeometry args={[data.dimensions[0],data.dimensions[1]]} />
      <meshBasicMaterial map={canvasMap} side={DoubleSide} transparent={true}/>
    </mesh>;

  } else if (axis == "y") {
    const offset_matrix = new Matrix4();
    offset_matrix.makeTranslation(-data.xRange._data[Math.floor(data.dimensions[0]/2)], 0, -data.zRange._data[Math.floor(data.dimensions[2]/2)]);

    const canvasMap = createTexture(slice, data.dimensions[0], data.dimensions[2], [data.windowLow, data.windowHigh]);
    canvasMap.minFilter = LinearFilter;
    canvasMap.wrapS = canvasMap.wrapT = ClampToEdgeWrapping;
    canvasMap.needsUpdate = true;

    const slice_position = new Matrix4().makeTranslation(0,0,data.yRange._data[sliceIndex]);
    const position = new Matrix4().makeRotationX(Math.PI/2).premultiply(offset_matrix).premultiply(matrix).multiply(slice_position);
    return <mesh matrixAutoUpdate={false} matrix={position} onPointerDown={onMouseDown} onPointerUp={onMouseUp}>
      <planeGeometry args={[data.dimensions[0],data.dimensions[2]]} />
      <meshBasicMaterial map={canvasMap} side={DoubleSide} transparent={true}/>
    </mesh>;

  } else if (axis == "x") {
    const offset_matrix = new Matrix4();
    offset_matrix.makeTranslation(0, -data.yRange._data[Math.floor(data.dimensions[1]/2)], -data.zRange._data[Math.floor(data.dimensions[2]/2)]);

    const canvasMap = createTexture(slice, data.dimensions[1], data.dimensions[2], [data.windowLow, data.windowHigh]);
    canvasMap.minFilter = LinearFilter;
    canvasMap.wrapS = canvasMap.wrapT = ClampToEdgeWrapping;
    canvasMap.needsUpdate = true;

    const slice_position = new Matrix4().makeTranslation(0,0,data.xRange._data[sliceIndex]);
    const position = new Matrix4().makeRotationY(-Math.PI/2).multiply(new Matrix4().makeRotationZ(-Math.PI/2)).premultiply(offset_matrix).premultiply(matrix).multiply(slice_position);
    return <mesh matrixAutoUpdate={false} matrix={position} onPointerDown={onMouseDown} onPointerUp={onMouseUp}>
      <planeGeometry args={[data.dimensions[1],data.dimensions[2]]} />
      <meshBasicMaterial map={canvasMap} side={DoubleSide} transparent={true}/>
    </mesh>;
  }
}

function VolumetricObject({data, matrix, cameraLock}) {
  const coordinateTransformation = new Matrix4();
  coordinateTransformation.set(-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1);
  
  const tform = math.transpose(math.inv(math.matrix(data.matrix.toArray()).reshape([4,4])));
  const invertedTForm = new Matrix4().set(...tform.reshape([16])._data);

  const geometry = new BoxGeometry( data.xRange._data.length, data.yRange._data.length, data.zRange._data.length );
  const material = new MeshBasicMaterial( { color: 0x00ff00 } );
  const cube = new Mesh( geometry, material );

  return <group matrixAutoUpdate={false} matrix={coordinateTransformation}>
    <boxHelper args={[cube, 0xffff00]}>
    </boxHelper>
    <VolumetricSlice data={data} sliceIndex={50} axis={"z"} matrix={invertedTForm} cameraLock={cameraLock} />
    <VolumetricSlice data={data} sliceIndex={255} axis={"y"} matrix={invertedTForm} cameraLock={cameraLock} />
    <VolumetricSlice data={data} sliceIndex={255} axis={"x"} matrix={invertedTForm} cameraLock={cameraLock} />
  </group>
}

export default VolumetricObject;