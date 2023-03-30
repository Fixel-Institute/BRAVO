/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, memo } from "react";

import MDInput from "components/MDInput"
import { dictionary } from "assets/translation"

function TextFilter({onFilter, language}) {
  const [filterOptions, setFilterOptions] = useState({});
    
  const handlePatientFilter = (event) => {
    setFilterOptions({value: event.currentTarget.value});
  }

  useEffect(() => {
    const filterTimer = setTimeout(() => {
      if (filterOptions.value) {
        const options = filterOptions.value.split(" ");
        onFilter(options);
      } else {
        onFilter([]);
      }
    }, 200);
    return () => clearTimeout(filterTimer);
  }, [filterOptions]);

  return <MDInput label={dictionary.Dashboard.SearchPatient[language]} value={filterOptions.text} onChange={(value) => handlePatientFilter(value)} sx={{paddingRight: 2}}/>
};

export default memo(TextFilter);