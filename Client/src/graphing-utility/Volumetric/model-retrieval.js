import { SessionController } from "database/session-control";
import { identityMatrix, computeElectrodePlacement, parseBinarySTL } from ".";
import * as THREE from "three";
import * as math from "mathjs";

/**
 * Wrapper for retriving models from UF BRAVO Platform Backend Server. 
 *
 * @param {string} directory - Directory that store the model. Typically the Patient ID.
 * @param {Object} item - The model object that describe the available models in the server. 
 * @param {string} color - Hex-encoded color string to force model into specific colors. 
 * 
 * @return {Object[]} Array of controllable items that contain both data and description of the model downloaded. 
 */
const retrieveModels = async (directory, item, color) => {
  const controlledItems = [];
  if (item.mode == "single") {
    
    if (item.type == "stl") {
      const response = await SessionController.query("/api/queryImageModel", {
        "Directory": directory,
        "FileName": item.file,
        "FileMode": item.mode,
        "FileType": item.type
      }, {}, null, "arraybuffer");
      const data = parseBinarySTL(response.data);
      controlledItems.push({
        filename: item.file,
        type: item.type,
        downloaded: true,
        data: data,
        opacity: 1,
        color: color ? color : data.color,
        matrix: identityMatrix(),
        show: true,
      });
    
    } else if (item.type == "volume") {
      const response = await SessionController.query("/api/queryImageModel", {
        "Directory": directory,
        "FileName": item.file,
        "FileMode": item.mode,
        "FileType": item.type
      }, {}, null, "arraybuffer");
      return response.data;

    } else if (item.type == "tracts") {
      const response = await SessionController.query("/api/queryImageModel", {
        "Directory": directory,
        "FileName": item.file,
        "FileMode": item.mode,
        "FileType": item.type
      });
      controlledItems.push({
        filename: item.file,
        type: item.type,
        downloaded: true,
        data: response.data.points,
        thickness: 1,
        color: color ? color : "#FFFFFF",
        matrix: identityMatrix(),
        show: true,
      });

    } else if (item.type == "points") {
      const response = await SessionController.query("/api/queryImageModel", {
        "Directory": directory,
        "FileName": item.file,
        "FileMode": item.mode,
        "FileType": item.type
      });
      controlledItems.push({
        filename: item.file,
        type: item.type,
        downloaded: true,
        data: response.data.points,
        thickness: 1,
        color: color ? color : "#FFFFFF",
        matrix: identityMatrix(),
        show: true,
      });

    } else if (item.type == "electrode") {
      const response = await SessionController.query("/api/queryImageModel", {
        "Directory": directory,
        "ElectrodeName": item.electrode,
        "FileName": item.file,
        "FileMode": item.mode,
        "FileType": item.type
      }, {}, null, "arraybuffer");
      const data = parseBinarySTL(response.data);
      controlledItems.push({
        filename: item.file,
        data: data,
        color: color ? color : data.color,
      });

    }
    return controlledItems;

  } else if (item.mode == "multiple") {

    if (item.type === "electrode") {
      const pagination = await SessionController.query("/api/queryImageModel", {
        "Directory": directory,
        "FileName": item.electrodeName,
        "FileMode": item.mode,
        "FileType": item.type
      });

      const targetPts = item.targetPt || [0,0,0];
      const entryPts = item.entryPt || [0,0,50];

      const electrode_data = {
        filename: item.file,
        type: item.type,
        downloaded: true,
        subname: [],
        data: [],
        color: color,
        opacity: 1,
        targetPts: targetPts,
        entryPts: entryPts,
        matrix: computeElectrodePlacement(targetPts, entryPts),
        show: true,
      };
      for (var page of pagination.data.pages) {
        const data = await retrieveModels(directory, {
          file: page.filename,
          electrode: page.electrode,
          mode: "single",
          type: page.type
        });
        electrode_data.subname.push(data[0].filename);
        electrode_data.data.push(data[0].data);
      }
      return [electrode_data]

    } else if (item.type === "volume") {
      const header_response = await SessionController.query("/api/queryImageModel", {
        "Directory": directory,
        "FileName": item.file,
        "FileMode": item.mode,
        "FileType": item.type
      });
      
      const volume = {};
      volume.header = header_response.data.headers;
      volume.dimensions = volume.header.size;
      volume.xRange = math.multiply(math.range(0,volume.header.size[0]), volume.header.pixdim[0]);
      volume.yRange = math.multiply(math.range(0,volume.header.size[1]), volume.header.pixdim[1]);
      volume.zRange = math.multiply(math.range(0,volume.header.size[2]), volume.header.pixdim[2]);
      volume.axisOrder = [ 'x', 'y', 'z' ];
      volume.spacing = volume.header.pixdim;
      volume.matrix = new THREE.Matrix4();
      volume.matrix.set(...volume.header.affine);
      
      const _data = await retrieveModels(directory, {
        file: item.file,
        mode: "single",
        type: item.type
      });

      volume.data = new Uint16Array(_data);
      let min = Infinity;
      let max = - Infinity;
      const datasize = volume.data.length;
      for ( var i = 0; i < datasize; i ++ ) {
        if ( ! isNaN( volume.data[ i ] ) ) {
          const value = volume.data[ i ];
          min = Math.min( min, value );
          max = Math.max( max, value );
        }
      }
      volume.lowerThreshold = min;
      volume.upperThreshold = max;
      volume.windowLow = min;
      volume.windowHigh = max;

      return [{
        filename: item.file,
        type: item.type,
        data: volume,
        color: "",
        matrix: identityMatrix(),
        show: true,
      }];
    }
  }
};

export default retrieveModels; 