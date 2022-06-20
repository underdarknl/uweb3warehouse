CREATE DATABASE  IF NOT EXISTS `warehouse` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `warehouse`;
-- MySQL dump 10.13  Distrib 8.0.29, for Linux (x86_64)
--
-- Host: localhost    Database: warehouse
-- ------------------------------------------------------
-- Server version	8.0.29-0ubuntu0.20.04.3

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `apiuser`
--

DROP TABLE IF EXISTS `apiuser`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `apiuser` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `key` char(32) NOT NULL,
  `active` enum('true','false') NOT NULL DEFAULT 'true',
  `name` varchar(45) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `key_UNIQUE` (`key`),
  UNIQUE KEY `name` (`name`),
  KEY `active` (`active`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product`
--

DROP TABLE IF EXISTS `product`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `sku` varchar(45) NOT NULL,
  `name` varchar(255) NOT NULL,
  `ean` char(13) DEFAULT NULL,
  `gs1` smallint unsigned DEFAULT NULL,
  `description` text,
  `assemblycosts` decimal(5,2) NOT NULL DEFAULT '0.00',
  `dateCreated` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateDeleted` datetime NOT NULL DEFAULT '1000-01-01 00:00:00',
  `vat` decimal(5,2) unsigned DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `sku_UNIQUE` (`sku`),
  UNIQUE KEY `gs1_UNIQUE` (`gs1`,`dateDeleted`)
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `productpart`
--

DROP TABLE IF EXISTS `productpart`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `productpart` (
  `ID` int unsigned NOT NULL AUTO_INCREMENT,
  `product` mediumint unsigned NOT NULL,
  `part` mediumint unsigned DEFAULT NULL,
  `amount` smallint unsigned NOT NULL,
  `assemblycosts` decimal(5,2) NOT NULL DEFAULT '0.00',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `product_part_uq` (`product`,`part`),
  KEY `product` (`product`),
  KEY `part` (`part`),
  CONSTRAINT `part` FOREIGN KEY (`part`) REFERENCES `product` (`ID`) ON UPDATE CASCADE,
  CONSTRAINT `product` FOREIGN KEY (`product`) REFERENCES `product` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `productprice`
--

DROP TABLE IF EXISTS `productprice`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `productprice` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `product` mediumint unsigned NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `start_range` mediumint unsigned DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `index3` (`product`,`start_range`),
  KEY `fk_productprice_1_idx` (`product`),
  CONSTRAINT `fk_productprice_1` FOREIGN KEY (`product`) REFERENCES `product` (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_0900_ai_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`warehouse`@`localhost`*/ /*!50003 TRIGGER `productprice_BEFORE_INSERT` BEFORE INSERT ON `productprice` FOR EACH ROW BEGIN
	IF (new.start_range != 1 and not exists(select * from warehouse.productprice where product=new.product and start_range=1))
		THEN SIGNAL SQLSTATE 'ERROR' set MESSAGE_TEXT = "You must first set the price of a single product before adding other ranges";
    END IF ;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `stock`
--

DROP TABLE IF EXISTS `stock`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `product` mediumint unsigned NOT NULL,
  `amount` mediumint NOT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `lot` varchar(45) DEFAULT NULL,
  `piece_price` decimal(10,2) unsigned DEFAULT NULL,
  `dateCreated` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `supplier`
--

DROP TABLE IF EXISTS `supplier`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `supplier` (
  `ID` tinyint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(45) NOT NULL,
  `website` varchar(255) DEFAULT NULL,
  `telephone` varchar(45) DEFAULT NULL,
  `contact_person` varchar(255) DEFAULT NULL,
  `email_address` varchar(255) DEFAULT NULL,
  `gscode` varchar(15) DEFAULT NULL,
  `dateDeleted` datetime NOT NULL DEFAULT '1000-01-01 00:00:00',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `name_UNIQUE` (`name`,`dateDeleted`)
) ENGINE=InnoDB AUTO_INCREMENT=132 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `supplierproduct`
--

DROP TABLE IF EXISTS `supplierproduct`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `supplierproduct` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `product` mediumint unsigned NOT NULL,
  `supplier` tinyint unsigned NOT NULL,
  `cost` decimal(10,2) DEFAULT NULL,
  `vat` decimal(4,2) NOT NULL DEFAULT '0.00',
  `name` varchar(255) NOT NULL,
  `lead` varchar(45) DEFAULT NULL,
  `supplier_stock` mediumint unsigned DEFAULT NULL,
  `supplier_sku` varchar(45) DEFAULT NULL,
  `datedeleted` datetime NOT NULL DEFAULT '1000-01-01 00:00:00',
  PRIMARY KEY (`ID`),
  KEY `fk_supplierproduct_1_idx` (`product`),
  KEY `fk_supplierproduct_2_idx` (`supplier`),
  CONSTRAINT `fk_supplierproduct_1` FOREIGN KEY (`product`) REFERENCES `product` (`ID`) ON UPDATE CASCADE,
  CONSTRAINT `fk_supplierproduct_2` FOREIGN KEY (`supplier`) REFERENCES `supplier` (`ID`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password` char(100) NOT NULL,
  `active` enum('true','false') NOT NULL DEFAULT 'true',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `email` (`email`),
  KEY `login` (`email`,`password`,`active`),
  KEY `active` (`active`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping events for database 'warehouse'
--

--
-- Dumping routines for database 'warehouse'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2022-06-14  8:46:49
