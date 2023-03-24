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