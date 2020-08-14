"""NGPVAN Bulk Import Endpoints"""
from parsons.etl.table import Table
from parsons.utilities import cloud_storage

import logging
import uuid

logger = logging.getLogger(__name__)


class BulkImport(object):

    def __init__(self):

        pass

    def get_bulk_import_resources(self):
        """
        Get bulk import resources that available to the user. These define
        the types of bulk imports that you can run. These might include
        ``Contacts``, ``ActivistCodes``, ``ContactsActivistCodes`` and others.

        `Returns:`
            list
                A list of resources.
        """

        r = self.connection.get_request(f'bulkImportJobs/resources')
        logger.info(f'Found {len(r)} bulk import resources.')
        return r

    def get_bulk_import_job(self, job_id):
        """
        Get a bulk import job status.

        `Args:`
            job_id : int
                The bulk import job id.
        `Returns:`
            dict
                The bulk import job
        """

        r = self.connection.get_request(f'bulkImportJobs/{job_id}')
        logger.info(f'Found bulk import job {job_id}.')
        return r

    def get_bulk_import_mapping_types(self):
        """
        Get bulk import mapping types.

        `Returns:`
            Parsons Table
                See :ref:`parsons-table` for output options.
        """

        tbl = Table(self.connection.get_request('bulkImportMappingTypes'))
        logger.info(f'Found {tbl.num_rows} bulk import mapping types.')
        return tbl

    def get_bulk_import_mapping_type(self, type_name):
        """
        Get a single bulk import mapping type.

        `Args:`
            type_name: str
        `Returns`:
            dict
                A mapping type json
        """

        r = self.connection.get_request(f'bulkImportMappingTypes/{type_name}')
        logger.info(f'Found {type_name} bulk import mapping type.')
        return r

    def post_bulk_import(self, tbl, url_type, resource_type, mapping_types,
                         description, **url_kwargs):
        # Internal method to post bulk imports. Specific types of imports call this
        # internal method.

        # Move to cloud storage
        file_name = str(uuid.uuid1())
        url = cloud_storage.post_file(tbl, url_type, file_path=file_name + '.zip', **url_kwargs)
        logger.info(f'Table uploaded to {url_type}.')

        # Generate request json
        json = {"description": description,
                "file": {
                    "columnDelimiter": 'csv',
                    "columns": [{'name': c} for c in tbl.columns],
                    "fileName": file_name + '.csv',
                    "hasHeader": "True",
                    "hasQuotes": "False",
                    "sourceUrl": url},
                "actions": [{"resultFileSizeKbLimit": 5000,
                             "resourceType": resource_type,
                             "actionType": "loadMappedFile",
                             "mappingTypes": mapping_types}]
                }

        r = self.connection.post_request('bulkImportJobs', json=json)
        logger.info(f"Bulk upload {r['jobId']} created.")
        return r['jobId']

    def bulk_apply_activist_codes(self, tbl, url_type, **url_kwargs):
        """
        Apply activist codes

        `Args:`
            table: Parsons table
                A Parsons table.
            url_type: str
                The cloud file storage to use to post the file. Currently only ``S3``.
            **url_kwargs: kwargs
                Arguments to configure your cloud storage url type.
                    * S3 requires ``bucket`` argument and, if not stored as env variables
                      ``aws_access_key`` and ``aws_secret_access_key``.
        `Returns:`
            int
                The bulk import job id
        """

        self.validate_first_column(tbl, "vanid")
        return self.post_bulk_import(tbl,
                                     url_type,
                                     'ContactsActivistCodes',
                                     [{"name": "ActivistCode"}],
                                     'Activist Code Upload',
                                     **url_kwargs)

    def validate_first_column(self, tbl, required_column):
        # The first column of a file is restricted based on the ResourceType and MappingType
        # and must match or be mapped to a specific column name. This method validates it.

        if tbl.columns[0].lower() != required_column:
            raise ValueError(f"First column name must be {required_column}")
